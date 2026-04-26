#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from pymongo import MongoClient

root = Path(__file__).resolve().parent.parent
sys.path.append(str(root))

from src.config import MongoConfig
from src.database.neo4j_client.connection import get_driver

def wipe_mongo():
    print("Connecting to MongoDB to wipe collections...")
    client = MongoClient(MongoConfig.MONGO_URI)
    db = client[MongoConfig.DB_NAME]
    
    collections_to_wipe = [
        MongoConfig.RAW_COLLECTION,
        MongoConfig.FORMATTED_COLLECTION,
        MongoConfig.ACTUAL_COLLECTION,
        MongoConfig.INTENT_COLLECTION,
        MongoConfig.UNIFIED_EVENTS_COLLECTION,
        'journal_entries',
        'agent_reflections'
    ]
    
    for col_name in collections_to_wipe:
        if col_name:
            print(f"Dropping MongoDB collection: {col_name}")
            db[col_name].drop()
            
    print("MongoDB collections wiped successfully.")

def wipe_neo4j():
    print("Connecting to Neo4j to wipe the graph...")
    driver = get_driver()
    if not driver:
        print("Could not connect to Neo4j. Skipping.")
        return
        
    with driver.session() as session:
        # DETACH DELETE all nodes to wipe the entire graph
        result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted_count")
        record = result.single()
        print(f"Deleted {record['deleted_count']} nodes from Neo4j.")
        
    print("Neo4j graph wiped successfully.")

if __name__ == "__main__":
    print("WARNING: This will completely wipe the MongoDB Calendar/Journal collections and the Neo4j Identity Graph.")
    confirm = input("Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() == 'yes':
        wipe_mongo()
        wipe_neo4j()
        print("Database wipe complete. Ready for multi-tenant state.")
    else:
        print("Aborted.")
