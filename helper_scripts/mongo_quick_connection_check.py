"""
Quick MongoDB connection health check.

Tests connectivity to Mongo Atlas and lists available databases.
"""
import sys
import os
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from dotenv import load_dotenv

# Load environment from .auth/.env using python-dotenv (consistent with rest of project)
root = Path(__file__).resolve().parent.parent
load_dotenv(root / ".auth" / ".env")

MONGO_URI = os.getenv("MONGO_URI")


def test_mongo_connection():
    """Verify MongoDB Atlas connectivity and list databases."""
    if not MONGO_URI:
        print("❌ ERROR: MONGO_URI is missing from .auth/.env")
        return

    try:
        # Establish connection with a 5 second timeout to fail fast
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

        # Issue a cheap ping command to the admin database
        client.admin.command('ping')
        print("✅ MongoDB Connection Successful! (GCP project can reach Mongo Atlas)")

        # Verify database access
        print("Available databases:")
        for db_name in client.list_database_names():
            print(f"  - {db_name}")

    except ConnectionFailure as e:
        print("❌ MongoDB Connection Timed Out! Ensure this IP is Whitelisted in Atlas Network Access.")
        print(f"   Details: {e}")
    except OperationFailure as e:
        print("❌ MongoDB Authentication Failed! Check username/password in MONGO_URI.")
        print(f"   Details: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


if __name__ == "__main__":
    test_mongo_connection()
