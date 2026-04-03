import os
import sys
from pathlib import Path
from datetime import datetime

# Path resolution
root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.database.mongo_storage import SovereignMongoStorage
from src.database.inject_hero_calendar import SovereignGraphInjector
from src.agents.gtky_librarian import GTKYLibrarian
from pymongo import UpdateOne

def run_sync_pipeline(hero_name=None):
    if hero_name is None:
        hero_name = os.environ.get("HERO_NAME", "Hero")
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
        # Phase 1/2: Gather Unstaged and Classify via Librarian
        raw_events = list(storage.raw_col.find({"sync_status": "staged"}))
        if raw_events:
            print(f"Librarian found {len(raw_events)} raw events awaiting classification.")
            golden_objects = librarian.classify_daily_batch(raw_events)
            
            # Save Golden Objects back to Mongo as 'formatted'
            if golden_objects:
                formatted_ops = []
                for obj in golden_objects:
                    formatted_ops.append(
                        UpdateOne(
                            {"gcal_id": obj.get('gcal_id')}, 
                            {"$set": obj}, 
                            upsert=True
                        )
                    )
                if formatted_ops:
                    storage.formatted_col.bulk_write(formatted_ops, ordered=False)
            
            # Mark raw as formatted
            raw_ops = []
            for raw in raw_events:
                raw_ops.append(
                    UpdateOne(
                        {"_id": raw["_id"]},
                        {"$set": {"sync_status": "formatted"}}
                    )
                )
            if raw_ops:
                storage.raw_col.bulk_write(raw_ops, ordered=False)
        else:
            print("No new raw events in Landing Zone to classify.")
            
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