import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dateutil import parser

# Path resolution
root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.database.mongo_storage import SovereignMongoStorage
from src.database.inject_hero_calendar import SovereignGraphInjector
from src.agents.gtky_librarian import GTKYLibrarian
from pymongo import UpdateOne

def run_sync_pipeline(target_date=None, target_user_email=None):
    if target_date is None:
        target_date = datetime.now(timezone.utc)
    elif isinstance(target_date, str):
        target_date = parser.parse(target_date)
    """
    The Master Orchestrator:
    1. Grabs staged events from Mongo.
    2. Passes them to GTKY Librarian for LLM classification.
    3. Saves Golden Objects to Mongo.
    4. Injects Formatted Data into Neo4j.
    5. Finalizes the sync status in Mongo.
    """
    print(f"--- Starting Sovereign Sync Pipeline for {hero_name} ---")
    print(f"Timestamp: {datetime.now().isoformat()}")

    storage = SovereignMongoStorage()
    injector = SovereignGraphInjector()
    librarian = GTKYLibrarian()
    
    from src.database.mongo_client.agent_health import AgentHeartbeatManager
    health_manager = AgentHeartbeatManager()
    run_id = health_manager.start_agent_run("calendar_sync_orchestrator", {"target_date": target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)})

    global_success = True
    
    try:
        users = storage.get_sync_opted_in_users()
        if target_user_email:
            users = [u for u in users if u.get("email") == target_user_email]
            
        if not users:
            print("No users opted in for calendar sync or target user not found.")
            global_success = True
        
        from src.database.calendar_raw_sync_to_mongo import SovereignCalendarSync
        cal_sync = SovereignCalendarSync()
        
        for user in users:
            user_email = user.get("email")
            refresh_token = user.get("google_refresh_token")
            hero_name = user.get("profile", {}).get("name", "Hero")
            
            print(f"--- Processing Sync for User: {user_email} ---")
            
            # Step 0: Pull from GCal using their credentials
            if refresh_token:
                try:
                    cal_sync.pull_recent_events(days=7, user_email=user_email, refresh_token=refresh_token)
                except Exception as e:
                    print(f"Failed to pull GCal events for {user_email}: {e}")
                    global_success = False
                    continue
            else:
                print(f"No refresh token for {user_email}, skipping GCal fetch.")
                # We don't fail global success here, just skip

            # Phase 1/2: Gather Unstaged for Target Date and Classify
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            from src.database.mongo_client.connection import MongoConnectionManager
            from src.config import MongoConfig
            db = MongoConnectionManager.get_db()
            timeseries_col = db[MongoConfig.RAW_TIMESERIES_COLLECTION]
            daily_cat_col = db[MongoConfig.DAILY_CATEGORIZED_EVENTS]
            
            raw_events_cursor = timeseries_col.find({
                "start_time": {"$gte": start_of_day, "$lt": end_of_day},
                "metadata.sync_status": "staged",
                "metadata.user_email": user_email
            })
            
            raw_events_list = list(raw_events_cursor)
            raw_events = [e.get("raw_data", {}) for e in raw_events_list]
            
            if raw_events:
                print(f"Librarian found {len(raw_events)} raw events on {start_of_day.date()} for {user_email}.")
                golden_objects = librarian.classify_daily_batch(raw_events)
                
                if golden_objects:
                    formatted_ops = []
                    daily_ops = []
                    for obj in golden_objects:
                        obj["user_email"] = user_email
                        formatted_ops.append(
                            UpdateOne(
                                {"gcal_id": obj.get('gcal_id')}, 
                                {"$set": obj}, 
                                upsert=True
                            )
                        )
                        obj['status'] = "Pending Verification"
                        daily_ops.append(
                            UpdateOne(
                                {"gcal_id": obj.get('gcal_id')},
                                {"$set": obj},
                                upsert=True
                            )
                        )
                    if formatted_ops:
                        storage.formatted_col.bulk_write(formatted_ops, ordered=False)
                    if daily_ops:
                        daily_cat_col.bulk_write(daily_ops, ordered=False)
                
                # Mark raw timeseries as formatted
                timeseries_ops = []
                for e in raw_events_list:
                    timeseries_ops.append(
                        UpdateOne(
                            {"_id": e["_id"]},
                            {"$set": {"metadata.sync_status": "formatted"}}
                        )
                    )
                if timeseries_ops:
                    timeseries_col.bulk_write(timeseries_ops, ordered=False)
            else:
                print(f"No new raw events in Timeseries Landing Zone for {user_email}.")
                
            # Phase 3: Identify events that haven't hit the Graph yet
            # Also filter by user_email in get_formatted_for_neo4j if possible, but let's just query direct
            formatted_events = list(storage.formatted_col.find({"neo4j_synced": {"$ne": True}, "user_email": user_email}))
            
            if not formatted_events:
                print(f"No new formatted events ready for Neo4j for {user_email}.")
                continue
                
            print(f"Attempting to inject {len(formatted_events)} events into the Identity Graph for {user_email}...")

            # Phase 4: Push to Neo4j
            injected_count = injector.inject_calendar_to_graph(formatted_events, hero_name=user_email)
            
            if injected_count > 0:
                gcal_ids = [e.get('gcal_id') for e in formatted_events if e.get('gcal_id')]
                if gcal_ids:
                    # Phase 5: Acknowledge sync in MongoDB
                    storage.formatted_col.update_many(
                        {"gcal_id": {"$in": gcal_ids}, "user_email": user_email},
                        {
                            "$set": {
                                "neo4j_synced": True, 
                                "neo4j_last_sync": datetime.now(timezone.utc)
                            }
                        }
                    )
                print(f"Successfully synchronized {injected_count} events to Neo4j.")
            else:
                print("Injection failed or no new nodes created. Check Neo4j logs.")
                global_success = False

    except Exception as e:
        print(f"Sync pipeline encountered an error: {e}")
        health_manager.end_agent_run(run_id, status="fail", error_msg=str(e))
        global_success = False
        raise e
    finally:
        injector.close()
        
        health_manager.end_agent_run(run_id, status="success" if global_success else "fail")
        
        try:
            storage.upsert_system_status("calendar_sync", {
                "status": "success" if global_success else "fail",
                "Sync_Integrity": global_success,
                "last_gcal_sync": datetime.now(timezone.utc).isoformat()
            })
        except Exception as log_e:
            print(f"Failed to log sync status: {log_e}")
            
        print("--- Pipeline Execution Finished ---")

if __name__ == "__main__":
    run_sync_pipeline()