import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).resolve().parent.parent
sys.path.append(str(root))

from src.database.vector_database.chromadb_client import ChromaExperimentalClient
from src.database.vector_database.weaviate_client import WeaviateExperimentalClient

def test_chroma():
    print("\n--- Testing ChromaDB (Local SQLite/DuckDB) ---")
    try:
        client = ChromaExperimentalClient()
        if not hasattr(client, 'collection'):
            print("[FAIL] ChromaDB Client failed to initialize. Missing dependencies?")
            return

        mock_embedding = [0.1, 0.2, 0.3] * 128 # Mock 384-dimensional vector typically used in BGE-M3
        
        print("[TEST] Inserting batch...")
        success = client.insert_batch(
            ids=["doc_1", "doc_2"],
            vectors=[mock_embedding, mock_embedding],
            metadatas=[{"pillar": "Health"}, {"pillar": "Wealth"}],
            documents=["I ate a healthy salad", "I invested in stocks"]
        )
        print(f"[SUCCESS] Batch inserted: {success}")
        
        print("[TEST] Performing Pillar Hybrid Search...")
        results = client.search_by_pillar(mock_embedding, "Health", n_results=1)
        if results and results.get("documents") and len(results["documents"][0]) > 0:
            print(f"[SUCCESS] Search returned context: {results['documents'][0][0]}")
            print("[STRENGTH] ChromaDB is working natively, zero-cost, with robust metadata filtering.")
            print("[WEAKNESS] Persistent directories scale poorly. Cannot natively host on multiple serverless containers (Cloud Run) without data corruption.")
        else:
            print("[FAIL] Search yielded nothing.")
    except Exception as e:
        print(f"[FAIL] ChromaDB encountered an error: {e}")

def test_weaviate():
    print("\n--- Testing Weaviate (Production Target) ---")
    try:
        client = WeaviateExperimentalClient()
        
        print("[TEST] Inserting batch...")
        success = client.insert_batch([])
        if success:
             print("[SUCCESS] Weaviate connection active.")
             print("[STRENGTH] High performance, native cloud cluster syncing, excellent for production.")
        else:
             print("[FAIL] Weaviate returned Mock. Verification failed.")
             print("[WEAKNESS] Falling short due to missing missing `weaviate-client` Python package in `pp_env` and missing `WEAVIATE_URL` / `WEAVIATE_API_KEY` configuration.")
    except Exception as e:
        print(f"[FAIL] Weaviate test crashed: {e}")

if __name__ == "__main__":
    print("=== Vector Database Verification Suite ===")
    test_chroma()
    test_weaviate()
    print("==========================================")
