import sys
from pathlib import Path
from datetime import datetime

# Path resolution
root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.database.mongo_storage import SovereignMongoStorage
from src.database.inject_hero_calendar import SovereignGraphInjector


from src.integrations.calendar_parser import parse_calendar_to_intentions
# Assuming you saved our Neo4j injection function from earlier here:

import os

def run_sync_pipeline(hero_name=None):
    if hero_name is None:
        hero_name = os.environ.get("HERO_NAME", "Hero")
    """
    The Master Orchestrator:
    1. Formats Raw Mongo Data.
    2. Injects Formatted Data into Neo4j.
    3. Finalizes the sync status in Mongo.
    """
    print(f"--- Starting Sovereign Sync Pipeline for {hero_name} ---")
    print(f"Timestamp: {datetime.now().isoformat()}")

    storage = SovereignMongoStorage()
    injector = SovereignGraphInjector()

    try:
        # Phase 1: Refresh the 'Formatted' collection from any new raw arrivals
        storage.process_all_unstaged()
        
        # Phase 2: Identify events that haven't hit the Graph yet
        formatted_events = storage.get_formatted_for_neo4j()
        
        if not formatted_events:
            print("No new formatted events ready for Neo4j. Pipeline complete.")
            return

        print(f"Attempting to inject {len(formatted_events)} events into the Identity Graph...")

        # Phase 3: Push to Neo4j
        injected_count = injector.inject_calendar_to_graph(formatted_events, hero_name=hero_name)
        
        if injected_count > 0:
            # Phase 4: Acknowledge sync in MongoDB to prevent double-injection
            gcal_ids = [e['gcal_id'] for e in formatted_events]
            storage.mark_neo4j_synced(gcal_ids)
            print(f"Successfully synchronized {injected_count} events to Neo4j and updated MongoDB.")
        else:
            print("Injection failed or no new nodes created. Check Neo4j logs.")

    finally:
        injector.close()
        print("--- Pipeline Execution Finished ---")



if __name__ == "__main__":
    run_sync_pipeline()