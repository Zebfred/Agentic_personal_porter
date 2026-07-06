#!/usr/bin/env python3
"""
Sovereign Schema Consolidation & Validation Engine
File: src/database/schema_consolidation.py
Operational Strategy: Enforces database purity, drop-wipes duplicate agent sprawl, 
                      and runs a local data sanity pass to ensure O(1) operational readiness.
"""
import os
import sys
from datetime import datetime
from pymongo import MongoClient, errors

# Absolute path configuration utilizing the Base Config pattern
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def execute_sovereign_consolidation():
    print("✨ Initiating System Collection Consolidation Protocol...")

    # 1. Establish Mongo Storage client via base environment variables
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        # Check deployment connection context immediately
        client.server_info()
        db = client["porter_collections"]
        print(f"✅ Connected to Local Landing Zone substrate at: {mongo_uri}")
    except errors.ServerSelectionTimeoutError:
        print("❌ Error: MongoDB deployment unreachable on target URI. Is the local instance active?")
        sys.exit(1)

    # 2. Hard target names for elimination (The sprawl cleanup list)
    sprawl_targets = [
        "calendar_actual_events",
        "calendar_intent_events",
        "calendar_unified_events",
        "daily_categorized_events",
        "formatted_calendar_events"
    ]

    existing_collections = db.list_collection_names()
    print(f"🔍 Discovered existing state collections: {existing_collections}")

    print("\n🔨 Purging redundant database targets...")
    for target in sprawl_targets:
        if target in existing_collections:
            db[target].drop()
            print(f" 🔥 Dropped duplicate staging workspace: '{target}'")
        else:
            print(f" ⏳ Sprawl target target '{target}' not present. Skipping.")

    # 3. Enforce Native Time-Series Collections for the Local Temporal Substrate
    print("\n🏗️ Building High-Fidelity Time-Series Constraints...")
    ts_collection = "calendar_events_timeseries"

    if ts_collection not in db.list_collection_names():
        try:
            db.create_collection(
                ts_collection,
                timeseries={
                    "timeField": "timestamp",
                    "metaField": "metadata",
                    "granularity": "seconds"
                }
            )
            print(f"✅ Created native Time-Series substrate: '{ts_collection}'")
        except Exception as e:
            print(f"⚠️ Failed to compile Time-Series parameters: {e}")
    else:
        print(f"✅ Time-Series collection '{ts_collection}' is structurally sovereign.")

    # 4. Enforce Baseline Indexes for Idempotency Checks
    print("\n⚡ Scaling Latency Indexes...")
    core_collections = ["event_intentions", "event_actuals", "unified_events"]
    for col in core_collections:
        # Enforce unique index mapping across global GCal resource IDs to eliminate data loops
        db[col].create_index([("gcal_id", 1)], unique=True, sparse=True)
        print(f" 📈 Applied unique constraint index [gcal_id] to collection: '{col}'")

    # 5. Local Data Handshake Sanity Pass (Simulating Local Operation)
    print("\n🧪 Executing Local State Ingestion Test...")
    mock_id = f"mock_evt_{int(datetime.utcnow().timestamp())}"

    mock_intention = {
        "gcal_id": mock_id,
        "title": "Deep RL System Architecture Focus",
        "duration_minutes": 120,
        "pillar": "Career Goal",
        "processed_at": datetime.utcnow().isoformat(),
        "record_type": "Intention"
    }

    try:
        # Idempotent database check
        db["event_intentions"].update_one(
            {"gcal_id": mock_id},
            {"$set": mock_intention},
            upsert=True
        )
        count = db["event_intentions"].estimated_document_count()
        print(f"✅ Local loop execution validated. Estimated Intention Document Count: {count}")
    except Exception as e:
        print(f"❌ Handshake Validation Failure: {e}")

    print("\n🚀 Database consolidation finalized. System workspace is clean.")

if __name__ == "__main__":
    # Security Sanity Audit: Check tracking boundary parameters
    if os.path.exists(".env") or os.path.exists("token.json"):
        print("🚨 SECURITY MISMATCH DETECTED: Sensitive environment tokens found outside your secure frontend path!")
        print("⚠️ Ensure credentials live in your local front-end environment and verify your git boundaries immediately.")
    execute_sovereign_consolidation()