# /tmp/test_neo4j_conn.py
import sys
import os
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.append(str(root))

from src.database.neo4j_client.connection import get_driver

def verify_connection():
    driver = get_driver()
    try:
        driver.verify_connectivity()
        print("✅ Neo4j Connection Successful!")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    verify_connection()
