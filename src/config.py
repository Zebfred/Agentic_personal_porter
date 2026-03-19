import os
from pathlib import Path
from dotenv import load_dotenv

from src.utils.path_utils import load_env_vars

# Find root and load .env once
load_env_vars()

class NeoConfig:
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USER = os.getenv("NEO4J_USERNAME")
    NEO4J_PASS = os.getenv("NEO4J_PASSWORD")

class MongoConfig:
    MONGO_URI = os.getenv("MONGO_URI")
    DB_NAME = "porter_mach2"
    RAW_COLLECTION = "raw_calendar_events"
    FORMATTED_COLLECTION = "formatted_calendar_events"