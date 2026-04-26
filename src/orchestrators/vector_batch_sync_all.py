import sys
from pathlib import Path
from datetime import datetime, timezone

root = Path(__file__).resolve().parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from src.integrations.embeddings_client import BGEM3EmbeddingsClient
from src.database.vector_database.chromadb_client import ChromaExperimentalClient
from src.database.vector_database.weaviate_client import WeaviateExperimentalClient
from src.database.mongo_client.connection import MongoConnectionManager
from src.integrations.gcp_compute_client import GCPComputeClient
from src.database.mongo_storage import SovereignMongoStorage

def execute_sync(sync_trigger_time: str = "NOON", limit: int = 20):
    """
    Pulls recent batches from MongoDB (journal_entries and agent_reflections),
    tags them, embeds them with BGE-M3.
    SEGREGATION RULE:
    - agent_reflections -> ChromaDB (Vibe check)
    - journal_entries -> Weaviate (Hybrid Search Intent/Actual tracking)
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting Isolated Vector Database Batch Sync: {sync_trigger_time}")
    
    from src.database.mongo_client.agent_health import AgentHeartbeatManager
    health_manager = AgentHeartbeatManager()
    run_id = health_manager.start_agent_run("vector_sync_orchestrator", {"sync_trigger_time": sync_trigger_time, "limit": limit})
    
    try:
        # 0. Wake up the massive BGE-M3 instance for vector generation
        cloud_client = GCPComputeClient()
        print("Sending wake pulse to Ollama Vector Host...")
        cloud_client.wake_instance("ollama-vector-host", block_until_running=True)

        db = MongoConnectionManager.get_db()
        journal_col = db["journal_entries"]
        reflections_col = db["agent_reflections"]
        
        raw_reflections = list(reflections_col.find().sort("created_at", -1).limit(limit))
        raw_journals = list(journal_col.find().sort("created_at", -1).limit(limit))
        
        print(f"Fetched {len(raw_reflections)} reflections and {len(raw_journals)} journal entries from Mongo.")
        
        # 1. Processing and homogenizing the Mongo documents
        chroma_items = []
        weaviate_items = []
        
        for doc in raw_reflections:
            reflection_text = doc.get("reflection_text", "")
            if not reflection_text: continue
            doc_id = str(doc.get("_id"))
            chroma_items.append({
                "id": f"reflection_{doc_id}",
                "text": reflection_text,
                "pillar": "Daily Reflection", 
                "source": "agent_reflection",
                "db_timestamp": str(doc.get("created_at", ""))
            })
            
        for doc in raw_journals:
            j_text = doc.get("text", "")
            if not j_text:
                j_intent = doc.get("intent", "")
                j_actual = doc.get("actual", "")
                j_text = f"Intent: {j_intent}. Actual: {j_actual}."
            doc_id = str(doc.get("_id"))
            weaviate_items.append({
                "id": f"journal_{doc_id}",
                "text": j_text,
                "pillar": doc.get("pillar", "Mundane Goal"), 
                "source": "journal_entry",
                "db_timestamp": str(doc.get("created_at", ""))
            })

        if not chroma_items and not weaviate_items:
            print("No processable text data found. Exiting.")
            health_manager.end_agent_run(run_id, status="success", result_summary="No data to sync.")
            return

        embeddings_client = BGEM3EmbeddingsClient()
        
        print("Beginning BGE-M3 target embedding generation...")
        for item in chroma_items + weaviate_items:
            item["embedding"] = embeddings_client.get_embedding(item["text"])
        
        # 4. Isolated Insertions 
        if chroma_items:
            chroma = ChromaExperimentalClient()
            chroma.insert_batch(
                ids=[r["id"] for r in chroma_items],
                vectors=[r["embedding"] for r in chroma_items],
                metadatas=[{"pillar": r["pillar"], "source": r["source"], "db_timestamp": r["db_timestamp"]} for r in chroma_items],
                documents=[r["text"] for r in chroma_items]
            )
            print(f"Pushed {len(chroma_items)} items to ChromaDB.")
            
        if weaviate_items:
            weaviate = WeaviateExperimentalClient()
            weaviate_vectors = [{"text": r["text"], "pillar": r["pillar"], "embedding": r["embedding"]} for r in weaviate_items]
            weaviate.insert_batch(weaviate_vectors)
            print(f"Pushed {len(weaviate_items)} items to Weaviate.")
        
        # 5. Shut down the heavy ML infrastructure to conserve budget
        print("Vector batch inserted! Stopping Ollama Vector Host to save costs.")
        cloud_client.sleep_instance("ollama-vector-host")
        
        # 6. Log Status
        try:
            storage = SovereignMongoStorage()
            storage.upsert_system_status("vector_db_sync", {
                "status": "success",
                "last_vector_sync": datetime.now(timezone.utc).isoformat(),
                "chroma_items_synced": len(chroma_items),
                "weaviate_items_synced": len(weaviate_items),
                "embedding_dimensions": len(chroma_items[0]["embedding"]) if chroma_items else (len(weaviate_items[0]["embedding"]) if weaviate_items else 0)
            })
        except Exception as log_e:
            print(f"Failed to log vector sync status: {log_e}")

        print("Isolated batch synchronization completed successfully.")
        health_manager.end_agent_run(run_id, status="success", result_summary=f"Synced {len(chroma_items)} to Chroma, {len(weaviate_items)} to Weaviate.")
        
    except Exception as e:
        print(f"Error during vector sync: {e}")
        health_manager.end_agent_run(run_id, status="fail", error_msg=str(e))
        raise e

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--trigger", type=str, default="MANUAL", choices=["NOON", "MIDNIGHT", "MANUAL"])
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    execute_sync(args.trigger, args.limit)
