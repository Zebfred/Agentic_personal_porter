from datetime import datetime, timezone
from pymongo import MongoClient
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from src.config import MongoConfig
from src.database.mongo_client.connection import MongoConnectionManager
from src.database.mongo_client.uuid_manager import UUIDGenerator
from src.integrations.calendar_parser import determine_category

class VectorStorageClient:
    """
    Handles interactions with the Vector DB backend (e.g., MongoDB Atlas Vector Search).
    This sets the foundation for the Corrector Agent and GTKY agent to do semantic "vibe" checks.
    """
    def __init__(self):
        self.db = MongoConnectionManager.get_db()
        self.vector_col = self.db[MongoConfig.VECTOR_DB_COLLECTION]

    def store_semantic_memory(self, memory_text: str, vector_embedding: list, metadata: dict = None):
        """
        Stores an embedded vector memory for future agent similarity search.
        """
        if metadata is None:
            metadata = {}
        
        doc = {
            "text": memory_text,
            "embedding": vector_embedding,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc)
        }
        return self.vector_col.insert_one(doc).inserted_id

    def search_similar_memories(self, query_embedding: list, limit: int = 5):
        """
        Stub for vector search. To be implemented fully with Atlas search index querying.
        """
        # Example aggregation pipeline for Atlas Vector Search
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding", 
                    "queryVector": query_embedding, 
                    "numCandidates": limit * 10, 
                    "limit": limit
                }
            }
        ]
        return list(self.vector_col.aggregate(pipeline))
