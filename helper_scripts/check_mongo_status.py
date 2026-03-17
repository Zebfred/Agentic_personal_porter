import sys
import os
from pymongo import MongoClient

# Ensure we can import from the src directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import MongoConfig

def verify_mongo_lake():
    print("✨ Checking MongoDB Raw Data Lake ✨\n")
    
    # Connect using your environment variables or local default
    MONGO_URI = MongoConfig.MONGO_URI
    client = MongoClient(MONGO_URI)
    db = client["porter_mach2"]
    collection = db["raw_calendar_events"]

    total_events = collection.count_documents({})
    unsynced_events = collection.count_documents({"neo4j_synced": {"$ne": True}})
    
    print(f"📦 Total Raw Events in Mongo: {total_events}")
    print(f"⏳ Events waiting to be pushed to Neo4j: {unsynced_events}")
    print("-" * 40)
    
    if total_events > 0:
        sample = collection.find_one()
        print("Sample Event Title:", sample.get("summary", "No Title"))
        print("Ingested At:", sample.get("porter_ingested_at", "Unknown"))
    
    client.close()

if __name__ == "__main__":
    verify_mongo_lake()