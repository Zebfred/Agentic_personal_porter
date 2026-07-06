from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os

class ChromaExperimentalClient:
    """
    Experimental client for ChromaDB Local DB.
    Tests in-house, zero-cost vector storage focusing on BGE-M3 and metadata filtering.
    """
    def __init__(self):
        self.persist_directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "chroma_db"
        )
        self.collection_name = "agentic_porter_memory"

        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except ImportError:
            logger.info("Warning: chromadb library not installed.")

    def insert_batch(self, ids: list[str], vectors: list[list[float]], metadatas: list[dict], documents: list[str]):
        """
        Embeddings and metadata are pushed synchronously.
        
        Note: Each entry in metadatas should include a 'correlation_id' key
        for cross-system data lineage tracking.
        """
        if hasattr(self, 'collection'):
            self.collection.add(
                ids=ids,
                embeddings=vectors,
                metadatas=metadatas,
                documents=documents
            )
            return True
        logger.info("Mock: Inserted batch to ChromaDB.")
        return False

    def search_by_pillar(self, query_vector: list[float], pillar_name: str, n_results: int = 5):
        """
        Hybrid search utilizing sparse metadata filtering for specific quality pillars.
        """
        if not hasattr(self, 'collection'):
            logger.info(f"Mock Chroma search by pillar: {pillar_name}")
            return []

        return self.collection.query(
            query_embeddings=[query_vector],
            n_results=n_results,
            where={"pillar": pillar_name}
        )

    def search_by_correlation_id(self, correlation_id: str) -> list:
        """
        Retrieves all vector entries linked to a specific correlation ID.
        Used for data lineage auditing — traces which embeddings originated
        from a given journal entry.
        
        Args:
            correlation_id: The cross-system lineage ID to search for.
            
        Returns:
            List of matching documents with their metadata.
        """
        if not hasattr(self, 'collection'):
            logger.info(f"Mock Chroma search by correlation_id: {correlation_id}")
            return []

        return self.collection.get(
            where={"correlation_id": correlation_id}
        )
