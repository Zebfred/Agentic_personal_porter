# API Reference

The Agentic Personal Porter utilizes two backend layers: the primary Flask server for daily intelligence aggregation, and an optional FastAPI microservice dedicated specifically to complex Retrieval-Augmented Generation (RAG).

## Core Flask Backend
**Base URL (Localhost):** `http://localhost:5000`

### `POST /process_journal`
Ingests a user's daily activity row, parses the metadata, and invokes the CrewAI agent loop.
- **Content-Type**: `application/json`
- **Payload Example**:
  ```json
  {
    "journal_entry": "Intention: Work on project. Activity: Coded for 2 hours.",
    "log_data": {
      "day": "monday",
      "timeChunk": "afternoon",
      "intention": "Work on project",
      "actual": "Coded for 2 hours",
      "feeling": "happy",
      "brainFog": 20,
      "isValuableDetour": false,
      "inventoryNote": ""
    }
  }
  ```
- **Response**: Triggers local database `MERGE` actions and returns the AI's empathy reflection string.

### `GET /get_calendar_events`
Extracts raw events from Google Calendar to aid the user in building initial Intentions.
- **Parameters**: `?date=YYYY-MM-DD`
- **Output**: Returns an array of calendar events occurring on that day. Automatically populates the front-end inputs.

---

## RAG Microservice
**Base URL (Localhost):** `http://localhost:8000`

### `GET /health`
Validates if the ChromaDB vector store is populated and the embeddings models are loaded.
- **Response**: `{"status": "healthy", "vector_store_size": 256, "service": "..."}`

### `POST /query`
Performs a semantic search and Groq-powered generation on the paper corpus.
- **Content-Type**: `application/json`
- **Payload Example**:
  ```json
  {
    "query": "What is Q-learning?",
    "top_k": 5
  }
  ```
- **Response**: Provides the AI's generated `"answer"`, an array of the `"sources"` referenced, and the `"similarity_score"` of those citations.

### `POST /rebuild_index`
Triggers the SciBERT engine to ingest the text corpus into ChromaDB chunks.
- **Parameters**: `?chunking_strategy=fixed`
- **Response**: The number of chunks successfully indexed.
