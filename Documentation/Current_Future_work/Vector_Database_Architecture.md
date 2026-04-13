# Vector Database and Embedding Architecture

This document preserves the architectural reasoning, budget constraints, and strategy for the Agentic Porter's long-term semantic memory, transitioning away from MongoDB Atlas to a custom HuggingFace ecosystem.

## Goal
Establish a high-performance, low-cost long-term memory for agents. The system must capture the semantic "vibe" of daily journal entries and calendar events, while explicitly measuring alignment with the 9 quality pillars of life sourced from the `Intent` object in `hero_ambition.json` (e.g. Social, Career, Health, Loved Ones, Leisure, Interest, Spiritual, Mundane).

## Vector Database Strategy: The Experimental Approach
Because cost limits and exact performance needs are still solidifying, we are doing foundational experimental testing on three vector databases simultaneously within `src/database/vector_database/`:

1.  **Pinecone (Serverless Starter)**: The anticipated front-runner. Excellent out-of-the-box Hybrid Search. Cost: $0/month on the starter plan with up to 2 million writes.
2.  **ChromaDB**: The open-source, "All-In-House" alternative. Hosted alongside the application, keeping costs strictly at $0.
3.  **Weaviate**: A vector-native object database that mimics relationships natively. Useful to test if "cross-references" between Journal Entries and Goal objects yield vastly superior hybrid retrievals compared to Pinecone.

Our goal is to run all three concurrently with mocked data to get hard numbers on performance/cost ratios before finalizing the production client.

## Batch Processing Architecture
To avoid constant database waking and token thrashing, vector embeddings will be compiled and injected strictly twice a day:
- **Noon (12:00 PM)**
- **Midnight (12:00 AM)**
Each batch processes the preceding 12-hours of 4-hour journal chunks and events.

## Embeddings Architecture (GCP & Local)

### Current Target: BGE-M3 (0.6B Parameters)
Highly performant for hybrid search. Low VRAM overhead. Fast enough to process our 4-hour journal chunks and 6-field calendar events in milliseconds. 
*   **Infrastructure:** Run on a GCP `e2-standard-2` Spot VM (2 vCPUs, 8 GB RAM).
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
