# Vector Database and Embedding Architecture

This document preserves the architectural reasoning, budget constraints, and strategy for the Agentic Porter's long-term semantic memory, transitioning away from MongoDB Atlas to a custom HuggingFace ecosystem.

## Goal
Establish a high-performance, low-cost long-term memory for agents. The system must capture the semantic "vibe" of daily journal entries and calendar events, while explicitly measuring alignment with the 9 quality pillars of life sourced from the `Intent` object in `hero_ambition.json` (e.g. Social, Career, Health, Loved Ones, Leisure, Interest, Spiritual, Mundane).

## Vector Database Strategy: The Hybrid Experimental Approach
Because cost limits and exact performance needs are still solidifying, we are doing foundational experimental testing running Vector DBs concurrently on simulated data. The active implementation runs via `scripts/vector_batch_sync_all.py` which executes the following segregation rule:

1.  **ChromaDB (Local, Open-Source)**: Used to store embeddings of **Agent Reflections**. This is to retain the semantic "Vibe check" of past AI feedback.
2.  **Weaviate (Local)**: Used to store embeddings of **Journal Entries**. Weaviate's object-native architecture mimics relationships, making it ideal for testing "cross-references" between Intent and Actual tracking.
3.  **Pinecone (Serverless Starter)**: Retained as a scalable backup option if local instances degrade under load.

## Batch Processing Architecture
To avoid constant database waking and token thrashing, the `vector_batch_sync_all.py` script pulls recent document batches from the MongoDB landing zone (the `journal_entries` and `agent_reflections` collections). 
Vector embeddings are compiled and injected strictly twice a day:
- **Noon (12:00 PM)**
- **Midnight (12:00 AM)**
Each batch processes the preceding 12-hours of 4-hour journal chunks and events.

## Embeddings Architecture (GCP & Local)

### Current Target: BGE-M3 (0.6B Parameters)
Highly performant for hybrid search. Low VRAM overhead. Fast enough to process our 4-hour journal chunks and 6-field calendar events in milliseconds. 
*   **Infrastructure:** Run on a GCP `e2-standard-2` Spot VM (2 vCPUs, 8 GB RAM) wrapping an Ollama/HuggingFace HTTP API.
*   **Integration:** Served locally via the `/api/embeddings` REST endpoint using `src/integrations/embeddings_client.py`.
*   **Pricing Strategy:** Spot Instance yields a 60-91% discount on compute, bringing the monthly embedding infrastructure to ~$5.00 – $9.00.

### Future Target: Qwen3-0.6B ("Deep Understanding" Agents)
While BGE-M3 serves the immediate workflow, future development will explicitly set up 1-3 agents dedicated to "deep understanding" of complex user context. These agents will use the **Qwen3-0.6B** model due to its massive 32k context window and high semantic clustering abilities for deeply reflective tasks. It comfortably runs on the same `e2-standard-2` CPU tier.

### Historical Comparison of Evaluated Models
*(Documented for future infrastructure reference)*

| Model | Size | Best GCE Tier | Strategy / Notes |
| :--- | :--- | :--- | :--- |
| **BGE-M3** | 0.6B | `e2-standard-2` | Run on CPU. Cheapest possible "always-on" option. (Current Front-Runner) |
| **nomic-embed** | 0.1B | `e2-micro` | Ultra-Budget. Might even fit in GCP's "Free Tier". |
| **Qwen3-0.6B** | 0.6B | `e2-standard-2` | Similar to BGE-M3; high context window (32k). **(Reserved for future deep-understanding agents)** |
| **Qwen2-7B** | 7B | `n1-standard-4` | Expensive. CPU is too slow (seconds per sentence), requiring an NVIDIA T4 GPU. Est. Cost: ~$250-$300/month (Must use Spot VMs to stay under $100). Dismissed for now due to cost. |
