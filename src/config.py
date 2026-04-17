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

# Activate LangSmith Tracing if API Key is detected
if os.getenv("LANGCHAIN_API_KEY") and os.getenv("LANGCHAIN_API_KEY") != "YOUR_API_KEY_HERE":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = "porter_mach_3"

class MongoConfig:
    MONGO_URI = os.getenv("MONGO_URI")
    DB_NAME = "porter_mach2"
    RAW_COLLECTION = "raw_calendar_events"
    FORMATTED_COLLECTION = "formatted_calendar_events"
    
    # New Event Schema Collections
    RAW_TIMESERIES_COLLECTION = "calendar_events_timeseries"
    INTENT_COLLECTION = "event_intentions"
    ACTUAL_COLLECTION = "event_actuals"
    UNIFIED_EVENTS_COLLECTION = "unified_events"
    
    # Vector DB Collection for Agents
    VECTOR_DB_COLLECTION = "semantic_vectors"