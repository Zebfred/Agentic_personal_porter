import os
import requests

class BGEM3EmbeddingsClient:
    """
    Client for generating embeddings via BGE-M3 (0.6B).
    Designed to point to a local Ollama/vLLM HTTP server running on a GCP e2-standard-2 Spot VM.
    """
    def __init__(self, endpoint_url: str = "http://localhost:11434/api/embeddings"):
        self.endpoint_url = os.getenv("BGE_M3_ENDPOINT", endpoint_url)
        self.model_name = "bge-m3"

    def get_embedding(self, text: str) -> list[float]:
        """
        Request the embedding from the local HuggingFace/Ollama service. 
        """
        payload = {
            "model": self.model_name,
            "prompt": text
        }
        try:
            response = requests.post(self.endpoint_url, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
        except requests.exceptions.RequestException as e:
            print(f"Failed to get BGE-M3 embedding... Returning mock vector of dim 1024 for testing. Error: {e}")
            return [0.0] * 1024 

    def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        # Helper to batch fetch embeddings 
        return [self.get_embedding(t) for t in texts]
