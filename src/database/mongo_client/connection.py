import os
from pymongo import MongoClient

# Attempt to load from src root
import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(root))

from src.config import MongoConfig

class MongoConnectionManager:
    """
    Singleton connection manager for MongoDB interactions.
    """
    _client = None

    @classmethod
    def get_client(cls) -> MongoClient:
        if cls._client is None:
            if not MongoConfig.MONGO_URI:
                raise ValueError("MONGO_URI is not set in environment or config.")
            cls._client = MongoClient(MongoConfig.MONGO_URI)
        return cls._client

    @classmethod
    def get_db(cls):
        return cls.get_client()[MongoConfig.DB_NAME]
