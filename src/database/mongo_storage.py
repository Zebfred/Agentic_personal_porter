import os
import sys
import json
from pymongo import MongoClient, UpdateOne
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
        self.journal_col = self.db['journal_entries']
        self.artifacts_col = self.db['hero_artifacts']

    def save_journal_entry(self, log_data: dict):
        """
        Saves a direct Journal Entry from the Frontend (Mach 2 App) into MongoDB.
        Returns the inserted object's string ID.
        """
        log_data["processed_at"] = datetime.now(timezone.utc)
        result = self.journal_col.insert_one(log_data)
        return str(result.inserted_id)

    def get_hero_artifact(self, artifact_name: str) -> dict:
        """
        Retrieves a JSON artifact from MongoDB. Returns None if not found.
        """
        doc = self.artifacts_col.find_one({"artifact_name": artifact_name}, {"_id": 0})
        return doc.get("data") if doc else None
        
    def save_hero_artifact(self, artifact_name: str, data: dict):
        """
        Saves or updates a JSON artifact in MongoDB.
        """
        self.artifacts_col.update_one(
            {"artifact_name": artifact_name},
            {"$set": {"data": data, "updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )

    def process_all_unstaged(self):
        """
        Iterates through the raw events in the Landing Zone and formats them for the Graph.
        Uses 'staged' status to track progress across the 13.5k event history.
        """
        # Find raw events not yet formatted
        raw_events = list(self.raw_col.find({"sync_status": "staged"}))
        
        print("--- Processing Raw Events for Formatting ((bulk upsert) ---")
        
        formatted_ops = []
        raw_ops = []
        success_count = 0
        batch_size = 1000  # Adjust based on performance testing
        for raw in raw_events:
            try:
                # The logic for 'HOW' to parse is delegated to calendar_parser.py
                fmt = parse_single_event(raw)
                
                if fmt:
                    formatted_ops.append(
                        UpdateOne(
                            {"gcal_id": fmt.get('gcal_id')}, 
                            {"$set": fmt}, 
                            upsert=True
                        )
                    )

                raw_ops.append(
                    UpdateOne(
                        {"_id": raw["_id"]},
                        {"$set": {"sync_status": "formatted"}}
                    )
                )
                
                success_count += 1
        
                if len(raw_ops) >= batch_size:
                    if formatted_ops:
                        self.formatted_col.bulk_write(formatted_ops, ordered=False)
                    if raw_ops:
                        self.raw_col.bulk_write(raw_ops, ordered=False)
                            
                    # Clear the lists for the next batch
                    formatted_ops = []
                    raw_ops = []
                    print(f"Beautifully processed batch... Total so far: {success_count}")

            except Exception as e:
                print(f"Minor hiccup processing raw event {raw.get('_id')}: {e}")         

        if formatted_ops:
            self.formatted_col.bulk_write(formatted_ops, ordered=False)
        if raw_ops:
            self.raw_col.bulk_write(raw_ops, ordered=False)
                
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
