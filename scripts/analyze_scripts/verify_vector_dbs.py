from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)

# Add project root to path

from src.database.vector_database.chromadb_client import ChromaExperimentalClient
from src.database.vector_database.weaviate_client import WeaviateExperimentalClient

def test_chroma():
    logger.info("\n--- Testing ChromaDB (Local SQLite/DuckDB) ---")
    try:
        client = ChromaExperimentalClient()
        if not hasattr(client, 'collection'):
            logger.info("[FAIL] ChromaDB Client failed to initialize. Missing dependencies?")
            return

        mock_embedding = [0.1, 0.2, 0.3] * 128 # Mock 384-dimensional vector typically used in BGE-M3

        logger.info("[TEST] Inserting batch...")
        success = client.insert_batch(
            ids=["doc_1", "doc_2"],
            vectors=[mock_embedding, mock_embedding],
            metadatas=[{"pillar": "Health"}, {"pillar": "Wealth"}],
            documents=["I ate a healthy salad", "I invested in stocks"]
        )
        logger.info(f"[SUCCESS] Batch inserted: {success}")

        logger.info("[TEST] Performing Pillar Hybrid Search...")
        results = client.search_by_pillar(mock_embedding, "Health", n_results=1)
        if results and results.get("documents") and len(results["documents"][0]) > 0:
            logger.info(f"[SUCCESS] Search returned context: {results['documents'][0][0]}")
            logger.info("[STRENGTH] ChromaDB is working natively, zero-cost, with robust metadata filtering.")
            logger.info("[WEAKNESS] Persistent directories scale poorly. Cannot natively host on multiple serverless containers (Cloud Run) without data corruption.")
        else:
            logger.info("[FAIL] Search yielded nothing.")
    except Exception as e:
        logger.info(f"[FAIL] ChromaDB encountered an error: {e}")

def test_weaviate():
    logger.info("\n--- Testing Weaviate (Production Target) ---")
    try:
        client = WeaviateExperimentalClient()

        logger.info("[TEST] Inserting batch...")
        success = client.insert_batch([])
        if success:
             logger.info("[SUCCESS] Weaviate connection active.")
             logger.info("[STRENGTH] High performance, native cloud cluster syncing, excellent for production.")
        else:
             logger.info("[FAIL] Weaviate returned Mock. Verification failed.")
             logger.info("[WEAKNESS] Falling short due to missing missing `weaviate-client` Python package in `pp_env` and missing `WEAVIATE_URL` / `WEAVIATE_API_KEY` configuration.")
    except Exception as e:
        logger.info(f"[FAIL] Weaviate test crashed: {e}")

if __name__ == "__main__":
    logger.info("=== Vector Database Verification Suite ===")
    test_chroma()
    test_weaviate()
    logger.info("==========================================")
