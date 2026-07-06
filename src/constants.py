from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
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
    client = MongoClient(MongoConfig.MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client[MongoConfig.DB_NAME]
    # Artifact name is stored as 'category_mapping' without '.json' in MongoDB
    doc = db["hero_artifacts"].find_one({"artifact_name": "category_mapping", "username": "system"}, {"_id": 0})
    if not doc:
        # Fallback to any user's category mapping (e.g. single-tenant / personal setup)
        doc = db["hero_artifacts"].find_one({"artifact_name": "category_mapping"}, {"_id": 0})

    if doc and "data" in doc:
        ACTUAL_CATEGORY_MAPPING = doc["data"]
        logger.info(f"Successfully loaded category mapping from MongoDB (user: {doc.get('username', 'system')}).")
    else:
        # Fallback to local files
        auth_file = root_dir / ".auth" / "category_mapping.json"
        example_file = root_dir / "data" / "category_mapping.example.json"

        loaded = False
        for filepath in [auth_file, example_file]:
            if filepath.exists():
                try:
                    with open(filepath, "r") as f:
                        ACTUAL_CATEGORY_MAPPING = json.load(f)
                    logger.info(f"Loaded category mapping from local fallback file: {filepath}")
                    loaded = True
                    break
                except Exception as file_err:
                    logger.warning(f"Error reading local category mapping fallback file {filepath}: {file_err}")

        if not loaded:
            logger.warning("category_mapping artifact not found in MongoDB or local files. Using empty fallback.")
            ACTUAL_CATEGORY_MAPPING = {"intent_to_actual_mapping": {}, "actual_categorization_with_keywords": {}, "colors": {}}
except Exception as e:
    logger.error(f"Error loading category mapping: {e}")
    ACTUAL_CATEGORY_MAPPING = {"intent_to_actual_mapping": {}, "actual_categorization_with_keywords": {}, "colors": {}}