import os
import sys
import json
#from zipfile import Path
from pymongo import MongoClient
from datetime import datetime, timezone, UTC
from pathlib import Path
    
# Ensure we can import from the src directory when running from helper_scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.config import MongoConfig
#from src.constants import ACTUAL_CATEGORY_MAPPING
from src.integrations.calendar_parser import parse_single_event 

# --- Mongo Setup ---

class SovereignMongoStorage:
    """
    Modern Mach 2 Storage Handler.
    Manages the transition from 'Raw' to 'Formatted' collections.
    This ensures the 'Raw Noise' of GCal is preserved while 'Formatted Signal'
    is prepared for the Neo4j Identity Graph.
    """
    def __init__(self) -> None:
        self.client = MongoClient(MongoConfig.MONGO_URI)
        self.db = self.client[MongoConfig.DB_NAME]
        self.mongo_uri = MongoConfig.MONGO_URI
        
        # Collection Pointers
        self.raw_col = self.db[MongoConfig.RAW_COLLECTION]
        self.formatted_col = self.db[MongoConfig.FORMATTED_COLLECTION]

    def process_all_unstaged(self):
        """
        Iterates through the raw events in the Landing Zone and formats them for the Graph.
        Uses 'staged' status to track progress across the 13.5k event history.
        """
        # Find raw events not yet formatted
        raw_events = self.raw_col.find({"sync_status": "staged"})
        
        print("--- Processing Raw Events for Formatting ---")
        
        success_count = 0
        for raw in raw_events:
            # The logic for 'HOW' to parse is delegated to calendar_parser.py
            formatted = parse_single_event(raw)
            
            if formatted:
                # Upsert into formatted collection to maintain idempotency
                self.formatted_col.update_one(
                    {"gcal_id": formatted['gcal_id']},
                    {"$set": formatted},
                    upsert=True
                )
                
                # Update status in raw collection to 'formatted' to mark completion
                self.raw_col.update_one(
                    {"_id": raw["_id"]},
                    {"$set": {"sync_status": "formatted"}}
                )
                success_count += 1
                
        print(f"Successfully formatted {success_count} events.")
        return success_count



    def get_formatted_for_neo4j(self):
        """
        A helper to fetch events from Mongo that haven't been 
        successfully processed into the Neo4j graph yet.
        """
        # Look for events where we haven't set a 'neo4j_synced' flag
        return list(self.formatted_col.find({"neo4j_synced": {"$ne": True}}))

    def mark_neo4j_synced(self, gcal_ids):
        """
        Finalizes the pipeline status once data hits the Neo4j Graph.
        """
        self.formatted_col.update_many(
            {"gcal_id": {"$in": gcal_ids}},
            {
                "$set": {
                    "neo4j_synced": True, 
                    "neo4j_last_sync": datetime.now(timezone.utc)
                }
            }
        )

# --- Execution Entry Point ---
if __name__ == "__main__":
        # Ensure environment variables are loaded if running manually
    #os.environ["MONGO_URI"] = 
    
    storage = SovereignMongoStorage()
    
    print(f"Sovereign Storage initiated at {datetime.now(timezone.utc)}")
    processed = storage.process_all_unstaged()
    
    # Final Verification
    if processed > 0:
        print(f"Ready for Graph Ingestion: {len(storage.get_formatted_for_neo4j())} events.")
