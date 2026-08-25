from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
from datetime import datetime, timezone
from dateutil import parser

# Path resolution

from src.database.mongo_storage import SovereignMongoStorage
from src.database.inject_hero_calendar import SovereignGraphInjector
from src.agents.gtky_librarian import GTKYLibrarian
from src.agents.gtky_historian import GTKYHistorian

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
    logger.info("--- Starting Sovereign Sync Pipeline ---")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    storage = SovereignMongoStorage()
    injector = SovereignGraphInjector()
    librarian = GTKYLibrarian()
    historian = GTKYHistorian()

    from src.database.mongo_client.agent_health import AgentHeartbeatManager
    health_manager = AgentHeartbeatManager()
    run_id = health_manager.start_agent_run("calendar_sync_orchestrator", {"target_date": target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)})

    global_success = True

    try:
        users = storage.get_sync_opted_in_users()
        if target_user_email:
            users = [u for u in users if u.get("email") == target_user_email]

        if not users:
            logger.info("No users opted in for calendar sync or target user not found.")
            global_success = True

        from src.database.calendar_raw_sync_to_mongo import SovereignCalendarSync
        cal_sync = SovereignCalendarSync()

        for user in users:
            user_email = user.get("email")
            refresh_token = user.get("google_refresh_token")
            username = user.get("username", "system")

            logger.info(f"--- Processing Sync for User: {user_email} ---")

            # Step 0: Pull from GCal using their credentials
            if refresh_token:
                try:
                    # Twin-Track: Pull Sliding Window (Now - 7d to Now + 30d)
                    cal_sync.pull_sliding_window(user_email=user_email, refresh_token=refresh_token)

                    # Twin-Track: Pull Historical Backlog (Cursor - 30d to Cursor)
                    oldest_cursor = storage.get_historical_sync_cursor(user_email)
                    ops_count, new_cursor = cal_sync.pull_historical_backlog(
                        user_email=user_email,
                        refresh_token=refresh_token,
                        oldest_cursor=oldest_cursor
                    )
                    storage.update_historical_sync_cursor(user_email, new_cursor)
                except Exception as e:
                    logger.info(f"Failed to pull GCal events for {user_email}: {e}")
                    global_success = False
                    continue
            else:
                logger.info(f"No refresh token for {user_email}, skipping GCal fetch.")
                # We don't fail global success here, just skip

            # Phase 1/2: Gather Unstaged and Classify (Twin-Tracked)
            start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            from src.database.mongo_client.connection import MongoConnectionManager
            from src.config import MongoConfig
            db = MongoConnectionManager.get_db()
            timeseries_col = db[MongoConfig.RAW_TIMESERIES_COLLECTION]
            daily_cat_col = db[MongoConfig.DAILY_CATEGORIZED_EVENTS]

            # Phase 3: Identify events that haven't hit the Graph yet from unified_events
            formatted_events = list(db["unified_events"].find({"neo4j_synced": {"$ne": True}, "user_id": user_email}))

            if not formatted_events:
                logger.info(f"No new formatted events ready for Neo4j for {user_email}.")
                continue

            logger.info(f"Attempting to inject {len(formatted_events)} events into the Identity Graph for {user_email}...")

            # Fetch username for partitioning
            user_doc = storage.get_user_by_email(user_email)
            username = user_doc.get("username", "unknown") if user_doc else "unknown"

            # Phase 4: Push to Neo4j
            injected_count = injector.inject_calendar_to_graph(formatted_events, user_email=user_email, username=username)

            if injected_count > 0:
                # Map gcal_ids correctly from the unified_events payload (can be inside intent or top level depending on event_processor)
                gcal_ids = []
                for e in formatted_events:
                    gcal_id = e.get('gcal_id')
                    if gcal_id:
                        gcal_ids.append(gcal_id)

                if gcal_ids:
                    # Phase 5: Acknowledge sync in MongoDB
                    db["unified_events"].update_many(
                        {"gcal_id": {"$in": gcal_ids}, "user_id": user_email},
                        {
                            "$set": {
                                "neo4j_synced": True,
                                "neo4j_last_sync": datetime.now(timezone.utc)
                            }
                        }
                    )
                logger.info(f"Successfully synchronized {injected_count} events to Neo4j.")
            else:
                logger.info("Injection failed or no new nodes created. Check Neo4j logs.")
                global_success = False

    except Exception as e:
        logger.info(f"Sync pipeline encountered an error: {e}")
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
            logger.info(f"Failed to log sync status: {log_e}")

        logger.info("--- Pipeline Execution Finished ---")

if __name__ == "__main__":
    run_sync_pipeline()