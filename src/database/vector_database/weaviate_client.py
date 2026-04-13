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
                self._ensure_schema()
            except ImportError:
                print("Warning: weaviate-client library not installed.")

    def _ensure_schema(self):
        schema = {
            "classes": [{
                "class": "MemoryObj",
                "description": "Agentic Porter Memory",
                "properties": [
                    {"name": "text", "dataType": ["text"]},
                    {"name": "pillar", "dataType": ["string"]}
                ]
            }]
        }
        if not self.client.schema.contains(schema):
            self.client.schema.create(schema)

    def insert_batch(self, memories: list[dict]):
        if hasattr(self, 'client'):
            with self.client.batch as batch:
                for mem in memories:
                    batch.add_data_object(
                        data_object={"text": mem["text"], "pillar": mem["pillar"]},
                        class_name="MemoryObj",
                        vector=mem["embedding"]
                    )
            return True
        print("Mock: Inserted batch to Weaviate.")
        return False

    def search_by_pillar(self, query_vector: list[float], pillar_name: str, limit: int = 5):
        if not hasattr(self, 'client'):
            print(f"Mock Weaviate search by pillar: {pillar_name}")
            return []
            
        result = (
            self.client.query
            .get("MemoryObj", ["text", "pillar"])
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
