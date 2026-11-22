import logging
import os
from typing import Any
from pymongo import MongoClient

from src.config import MongoConfig

logger = logging.getLogger(__name__)


class MongoConnectionManager:
    """
    Singleton connection manager for MongoDB interactions with fast local
    timeout and automatic `mongomock` dev fallback when `localhost:27017`
    is unreachable or `MONGO_USE_MOCK=true`.
    """

    _client: Any = None

    @classmethod
    def get_client(cls) -> Any:
        if cls._client is None:
            use_mock = os.environ.get("MONGO_USE_MOCK", "").strip().lower() in ("1", "true", "yes")
            if use_mock:
                import mongomock

                cls._client = mongomock.MongoClient()
                return cls._client

            if not MongoConfig.MONGO_URI:
                raise ValueError("MONGO_URI is not set in environment or config.")

            uri = MongoConfig.MONGO_URI
            is_local = "localhost" in uri or "127.0.0.1" in uri
            timeout_ms = 2500 if is_local else 10000
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=timeout_ms,
                connectTimeoutMS=timeout_ms,
                socketTimeoutMS=timeout_ms,
            )
            if is_local:
                try:
                    client.admin.command("ping")
                except Exception as exc:
                    try:
                        import mongomock

                        logger.warning(
                            "Local MongoDB (%s) unreachable (%s); falling back to in-memory mongomock for local session.",
                            uri,
                            exc,
                        )
                        cls._client = mongomock.MongoClient()
                        return cls._client
                    except ImportError:
                        logger.warning("mongomock not installed; proceeding with MongoClient.")
            cls._client = client
        return cls._client

    @classmethod
    def get_db(cls) -> Any:
        return cls.get_client()[MongoConfig.DB_NAME]
