# Active MongoDB Vector Database Implementation Plan

This document outlines the step-by-step implementation plan for expanding the existing MongoDB cluster into a production-ready Vector Database. This will serve as the long-term semantic "vibe" memory for the Agentic Porter ecosystem (e.g., Corrector and GTKY agents).

## Goal
To upgrade `src/database/mongo_client/vector_storage.py` from a skeleton schema to a fully functional vector storage and retrieval system, backed by a MongoDB Atlas Vector Search Index.

## Proposed Changes

### Phase 1: Embedding Integration & Vector Storage

We need to add the capability to convert agent strings into embeddings before they interact with MongoDB.

#### [MODIFY] `src/database/mongo_client/vector_storage.py`
- **Add Initialization:** Initialize the chosen embedding model within the `VectorStorageClient` `__init__`.
- **Update Insert Logic:** Modify `store_semantic_memory(self, memory_text: str, metadata: dict = None)` to automatically generate the `vector_embedding` from the text instead of requiring it as an input.
- **Update Search Logic:** Modify `search_similar_memories(self, query_text: str, limit: int = 5)` to compute the vector of the query text and execute the `$vectorSearch` pipeline.
- **Metadata Schema:** Formalize metadata to track `"source"`, `"agent"`, and `"salience"`.

### Phase 2: Atlas Vector Search Index Setup

We must construct the exact Index JSON schema needed to enable IVF/PQ on the MongoDB Atlas Dashboard.

#### [NEW] `Documentation/vector_index_schema.json`
Create a reference JSON file containing the exact schema to copy/paste into the MongoDB Atlas UI.
```json
{
  "fields": [
    {
      "numDimensions": 1536, // or 384 depending on model chosen
      "path": "embedding",
      "similarity": "cosine",
      "type": "vector"
    }
  ]
}
```
*(Note: Atlas currently handles quantization and index types automatically under the hood for dedicated tiers, but we will document the exact schema requirements for the cluster).*

### Phase 3: Agent Integration
Hook the `VectorStorageClient` into the GTKY/Corrector agent tools.

## Open Questions

1. Do you want to use OpenAI or local HuggingFace sentence-transformers for the embedding step?
2. Are you using a free/shared MongoDB Atlas cluster (M0) or a dedicated tier? (This impacts which Atlas vector search features like IVF are available).

## Verification Plan
1. Test embedding generation.
2. Insert 3 mock memories into Mongo.
3. Successfully run `$vectorSearch` to fetch them back accurately.
