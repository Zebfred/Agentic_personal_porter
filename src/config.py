import os
from pathlib import Path
from dotenv import load_dotenv

# Find root and load .env once
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".auth" / ".env")

class NeoConfig:
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USER = os.getenv("NEO4J_USERNAME")
    NEO4J_PASS = os.getenv("NEO4J_PASSWORD")

class MongoConfig:
    MONGO_URI = os.getenv("MONGO_URI")
    DB_NAME = "porter_mach2"
    RAW_COLLECTION = "raw_calendar_events"
    FORMATTED_COLLECTION = "formatted_calendar_events"