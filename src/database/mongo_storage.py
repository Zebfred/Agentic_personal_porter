import os
import json
from pymongo import MongoClient
from datetime import datetime
from src.config import Config

# Ensure we can import from the src directory when running from helper_scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Mongo Setup ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["personal_porter"]
collection = db["raw_calendar_events"]

def stage_raw_events(raw_events):
    """
    Upserts raw Google Calendar events into MongoDB.
    Uses the Google 'id' as the '_id' to prevent duplicates.
    """
    if not raw_events:
        print("⚠️ No raw events provided for staging.")
        return 0

    ops_count = 0
    for event in raw_events:
        # We use the event ID as the document ID for automatic deduplication
        event_id = event.get('id')
        if not event_id:
            continue
            
        # Add a local ingestion timestamp for auditing
        event['porter_ingested_at'] = datetime.timezone.utc.utcnow()
        
        # Replace if exists, insert if new
        collection.replace_one({'_id': event_id}, event, upsert=True)
        ops_count += 1
        
    print(f"📦 Staged {ops_count} raw events in MongoDB.")
    return ops_count

def get_unstaged_events_for_neo4j():
    """
    A helper to fetch events from Mongo that haven't been 
    successfully processed into the Neo4j graph yet.
    """
    # Look for events where we haven't set a 'neo4j_synced' flag
    return list(collection.find({"neo4j_synced": {"$ne": True}}))

def mark_as_synced(event_ids):
    """Updates Mongo records to acknowledge they've hit the graph."""
    collection.update_many(
        {"_id": {"$in": event_ids}},
        {"$set": {"neo4j_synced": True, "neo4j_last_sync": datetime.timezone.utc.utcnow()}}
    )

# --- Local Verification ---
if __name__ == "__main__":
    # Test with a dummy raw event
    test_raw = [{
        "id": "sample_gcal_id_001",
        "summary": "Deep Dive on LaUIrl",
        "start": {"dateTime": "2026-03-11T14:00:00Z"},
        "updated": "2026-03-11T15:00:00Z",
        "colorId": "9"
    }]
    stage_raw_events(test_raw)