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

def execute_sync(sync_trigger_time: str = "NOON", limit: int = 20):
    """
    Pulls recent batches from MongoDB (journal_entries and agent_reflections),
    tags them, embeds them with BGE-M3.
    SEGREGATION RULE:
    - agent_reflections -> ChromaDB (Vibe check)
    - journal_entries -> Weaviate (Hybrid Search Intent/Actual tracking)
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting Isolated Vector Database Batch Sync: {sync_trigger_time}")
    
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
    
    print("Isolated batch synchronization completed successfully.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--trigger", type=str, default="MANUAL", choices=["NOON", "MIDNIGHT", "MANUAL"])
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    execute_sync(args.trigger, args.limit)
