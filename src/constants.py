import logging
from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os
from pathlib import Path

# Find root
root_dir = Path(__file__).resolve().parent.parent
import json

from pymongo import MongoClient
from src.config import MongoConfig

# --- THE LIFE PILLAR MAP ---
# This is the "Learning" base. We map keywords and Google Colors to Pillars.
# We load ACTUAL_CATEGORY_MAPPING dynamically from MongoDB (Sovereign Mongo Storage representation).
try:
    client = MongoClient(MongoConfig.MONGO_URI)
    db = client[MongoConfig.DB_NAME]
    # Artifact name is stored as 'category_mapping' without '.json' in MongoDB
    doc = db["hero_artifacts"].find_one({"artifact_name": "category_mapping", "username": "system"}, {"_id": 0})
    if doc and "data" in doc:
        ACTUAL_CATEGORY_MAPPING = doc["data"]
        logger.info("Successfully loaded category mapping from MongoDB.")
    else:
        logger.warning("category_mapping artifact not found in MongoDB hero_artifacts. Using empty fallback.")
        ACTUAL_CATEGORY_MAPPING = {"intent_to_actual_mapping": {}, "actual_categorization_with_keywords": {}, "colors": {}}
except Exception as e:
    logger.error(f"Error loading category mapping from MongoDB: {e}")
    ACTUAL_CATEGORY_MAPPING = {"intent_to_actual_mapping": {}, "actual_categorization_with_keywords": {}, "colors": {}}