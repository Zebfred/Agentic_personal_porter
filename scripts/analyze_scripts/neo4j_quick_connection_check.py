# /tmp/test_neo4j_conn.py
import logging
from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import sys
import os
from pathlib import Path

# Add project root to sys.path

from src.database.neo4j_client.connection import get_driver

def verify_connection():
    driver = get_driver()
    try:
        driver.verify_connectivity()
        logger.info("✅ Neo4j Connection Successful!")
    except Exception as e:
        logger.info(f"❌ Connection Failed: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    verify_connection()
