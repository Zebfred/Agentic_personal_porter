import logging
from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os
import sys
import json
from pathlib import Path

# Add project root to sys.path

from src.database.mongo_storage import SovereignMongoStorage

def seed_mongo():
    logger.info("Initiating MongoDB Artifact Seeding...")
    try:
        ms = SovereignMongoStorage()
        logger.info(f"Connected to DB: {ms.db.name}")
        
        artifacts_to_seed = ['hero_ambition.json', 'hero_origin.json']
        
        for art in artifacts_to_seed:
            path = os.path.join('data', 'hero_artifacts', art)
            if not os.path.exists(path):
                logger.info(f"File not found: {path}")
                continue
                
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            logger.info(f"Loaded {art}, attempting to save to MongoDB...")
            ms.save_hero_artifact(art, data)
            logger.info(f"Successfully saved {art} to MongoDB!")
            
    except Exception as e:
        logger.info(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    seed_mongo()
