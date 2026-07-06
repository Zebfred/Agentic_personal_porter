from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os

class WeaviateExperimentalClient:
    """
    Experimental client for Weaviate Vector-Native Object Database.
    Tests if cross-references and native hybrid search yield functionally better vibe checks.
    """
    def __init__(self):
        self.cluster_url = os.getenv("WEAVIATE_URL", "mock-url")
        self.api_key = os.getenv("WEAVIATE_API_KEY", "mock-key")

        if self.cluster_url != "mock-url":
            try:
                import weaviate
                self.client = weaviate.Client(
                    url=self.cluster_url,
                    auth_client_secret=weaviate.AuthApiKey(api_key=self.api_key)
                )
                # self._ensure_schema() # Disabled to prevent hitting Sandbox 1-collection limit
            except ImportError:
                logger.info("Warning: weaviate-client library not installed.")

    def _ensure_schema(self):
        schema = {
            "classes": [{
                "class": "MemoryObj",
                "description": "Agentic Porter Memory",
                "properties": [
                    {"name": "text", "dataType": ["text"]},
                    {"name": "pillar", "dataType": ["string"]},
                    {"name": "correlation_id", "dataType": ["string"]}
                ]
            }]
        }
        if not self.client.schema.contains(schema):
            self.client.schema.create(schema)

        private_brain_class = {
            "class": "PrivateBrainObj",
            "description": "Private Brain documentation and scripts",
            "properties": [
                {"name": "text", "dataType": ["text"]},
                {"name": "source_type", "dataType": ["string"]},
                {"name": "folder", "dataType": ["string"]},
                {"name": "filename", "dataType": ["string"]}
            ]
        }
        if not self.client.schema.exists("PrivateBrainObj"):
            self.client.schema.create_class(private_brain_class)

    def insert_batch(self, memories: list[dict]):
        """
        Insert memory embeddings with metadata.
        
        Note: Each entry in memories should include a 'correlation_id' key
        for cross-system data lineage tracking.
        """
        if hasattr(self, 'client'):
            with self.client.batch as batch:
                for mem in memories:
                    batch.add_data_object(
                        data_object={
                            "text": mem["text"],
                            "pillar": mem["pillar"],
                            "correlation_id": mem.get("correlation_id", "")
                        },
                        class_name="MemoryObj",
                        vector=mem["embedding"]
                    )
            return True
        logger.info("Mock: Inserted batch to Weaviate.")
        return False

    def search_by_pillar(self, query_vector: list[float], pillar_name: str, limit: int = 5):
        if not hasattr(self, 'client'):
            logger.info(f"Mock Weaviate search by pillar: {pillar_name}")
            return []

        result = (
            self.client.query
            .get("MemoryObj", ["text", "pillar", "correlation_id"])
            .with_near_vector({"vector": query_vector})
            .with_where({
                "path": ["pillar"],
                "operator": "Equal",
                "valueString": pillar_name
            })
            .with_limit(limit)
            .do()
        )
        return result

    def search_by_correlation_id(self, correlation_id: str, limit: int = 10):
        """
        Retrieves all vector entries linked to a specific correlation ID.
        Used for data lineage auditing.
        
        Args:
            correlation_id: The cross-system lineage ID to search for.
            limit: Max number of results.
            
        Returns:
            Weaviate query result dict.
        """
        if not hasattr(self, 'client'):
            logger.info(f"Mock Weaviate search by correlation_id: {correlation_id}")
            return []

        result = (
            self.client.query
            .get("MemoryObj", ["text", "pillar", "correlation_id"])
            .with_where({
                "path": ["correlation_id"],
                "operator": "Equal",
                "valueString": correlation_id
            })
            .with_limit(limit)
            .do()
        )
        return result

    def insert_private_brain_batch(self, documents: list[dict]):
        if hasattr(self, 'client'):
            with self.client.batch as batch:
                for doc in documents:
                    batch.add_data_object(
                        data_object={
                            "text": doc["text"],
                            "source_type": doc.get("source_type", "private_brain"),
                            "folder": doc.get("folder", "unknown"),
                            "filename": doc.get("filename", "unknown")
                        },
                        class_name="PrivateBrainObj",
                        vector=doc["embedding"]
                    )
            return True
        logger.info("Mock: Inserted batch to Weaviate PrivateBrainObj.")
        return False

    def search_private_brain(self, query_vector: list[float], limit: int = 3):
        if not hasattr(self, 'client'):
            logger.info("Mock Weaviate search for private brain")
            return []

        result = (
            self.client.query
            .get("PrivateBrainObj", ["text", "filename", "folder"])
            .with_near_vector({"vector": query_vector})
            .with_where({
                "path": ["source_type"],
                "operator": "Equal",
                "valueString": "private_brain"
            })
            .with_limit(limit)
            .do()
        )
        return result

