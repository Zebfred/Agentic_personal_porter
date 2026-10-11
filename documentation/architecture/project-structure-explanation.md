# Project Structure Explanation

The Agentic Personal Porter's architecture emphasizes a clean separation of concerns, ensuring that distinct subsystems operate independently while interacting cohesively. Here is a breakdown of the primary directories and their specific responsibilities.

## `Documentation/`
The localized hub for all project knowledge, separated semantically rather than chronologically:
- **`architecture/`**: High-level system design documents, database schemas, agent registries, and operational protocols.
- **`development/`**: Onboarding material, API references, security checklists, and developer guides.
- **`features/`**: Instructions and implementation details for specific robust components (like the RAG service).
- **`notes/`**: A chronological archive of historical sprint check-ins and reflection logs.
- **`txt_notes/`**: Unaltered raw text notes spanning various topics.

## `src/`
The core backend nervous system powered by Python. 
- **`main.py` & `server.py`**: The Flask entry points handling REST requests from the client.
- **`integrations/`**: Encompasses external tool bridges, such as the Google Calendar authentication helper (`google_calendar.py`).
- **`database/`**: Dedicated Neo4j logic (`neo4j_db.py`). Contains connection boilerplate and the execution paths for injecting data.

## `frontend/`
The user-facing presentation layer.
- Designed as a lightweight HTML/JS/Tailwind stack.
- `index.html` operates as the primary logging form while `inventory.html` provides the visual "Hero's Stats" and gathered achievements.
- `app.js` handles async fetch logic and client-side DOM sanitization.

## `.auth/`
**Critical Security Layer.**
Contains highly sensitive, sovereign user data. This directory is entirely `git ignored`.
- Contains `.env` items (Groq API keys, Neo4j URIs).
- Contains Google OAuth tokens (`token.json`, `credentials.json`).

## `rag_system/`
The isolated infrastructure for robust mathematical and conceptual processing. 
Contains its own FastAPI microservice architecture, Docker deployment strategy, ChromaDB vector store generation logic, and SciBERT embeddings tailored for complex scientific or programmatic documents.
