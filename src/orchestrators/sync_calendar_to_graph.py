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

def run_sync_pipeline(hero_name=None, target_date=None):
    if hero_name is None:
        hero_name = os.environ.get("HERO_NAME", "Hero")
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

    try:
        # Phase 1/2: Gather Unstaged for Target Date and Classify via Librarian
        # Mach 3 Rework: Pull bounded by target_date from time-series to avoid 13k backlog crash.
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        from src.database.mongo_client.connection import MongoConnectionManager
        from src.config import MongoConfig
        db = MongoConnectionManager.get_db()
        timeseries_col = db[MongoConfig.RAW_TIMESERIES_COLLECTION]
        daily_cat_col = db[MongoConfig.DAILY_CATEGORIZED_EVENTS]
        
        raw_events_cursor = timeseries_col.find({
            "start_time": {"$gte": start_of_day, "$lt": end_of_day},
            "metadata.sync_status": "staged"
        })
        
        # Flatten timeseries structure back to what Librarian expects (raw_data)
        raw_events = [e.get("raw_data", {}) for e in raw_events_cursor]
        
        if raw_events:
            print(f"Librarian found {len(raw_events)} raw events on {start_of_day.date()} awaiting classification.")
            golden_objects = librarian.classify_daily_batch(raw_events)
            
            # Save Golden Objects back to Mongo
            if golden_objects:
                formatted_ops = []
                daily_ops = []
                for obj in golden_objects:
                    # Staging layer for graph
                    formatted_ops.append(
                        UpdateOne(
                            {"gcal_id": obj.get('gcal_id')}, 
                            {"$set": obj}, 
                            upsert=True
                        )
                    )
                    # Specific daily collection for Verification Dashboard
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
            raw_events_cursor.rewind()
            for e in raw_events_cursor:
                timeseries_ops.append(
                    UpdateOne(
                        {"_id": e["_id"]},
                        {"$set": {"metadata.sync_status": "formatted"}}
                    )
                )
            if timeseries_ops:
                timeseries_col.bulk_write(timeseries_ops, ordered=False)
        else:
            print(f"No new raw events in Timeseries Landing Zone for {start_of_day.date()} to classify.")
            
        # Phase 3: Identify events that haven't hit the Graph yet
        formatted_events = storage.get_formatted_for_neo4j()
        
        if not formatted_events:
            print("No new formatted events ready for Neo4j. Pipeline complete.")
            return

        print(f"Attempting to inject {len(formatted_events)} events into the Identity Graph...")

        # Phase 4: Push to Neo4j via UNWIND logic
        injected_count = injector.inject_calendar_to_graph(formatted_events, hero_name=hero_name)
        
        if injected_count > 0:
            # Phase 5: Acknowledge sync in MongoDB to prevent double-injection
            gcal_ids = [e.get('gcal_id') for e in formatted_events if e.get('gcal_id')]
            if gcal_ids:
                storage.mark_neo4j_synced(gcal_ids)
            print(f"Successfully synchronized {injected_count} events to Neo4j and updated MongoDB.")
        else:
            print("Injection failed or no new nodes created. Check Neo4j logs.")

    finally:
        injector.close()
        print("--- Pipeline Execution Finished ---")

if __name__ == "__main__":
    run_sync_pipeline()