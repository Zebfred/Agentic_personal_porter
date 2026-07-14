# Agentic Personal Porter

## Introduction & Vision

Welcome, Hero. Your journey is uniquely yours, and every step, planned or unplanned, holds value. The Agentic Personal Porter is your non-judgmental digital companion on this adventure. It isn't just another productivity tracker—it is a sovereign intelligence layer designed to compassionately bridge the gap between your stated intentions and your actual actions.

By leveraging holistic frameworks like Maslow's Hierarchy of Needs and extracting deep context from your "Origin Story" and "Ambitions," we aim to capture a nuanced picture of your state. The Porter helps you understand the "why" behind your choices, find meaning in what you do, and align your daily grind with a fulfilling existence.

## The Mach 4 Ecosystem (Current Architecture)

We are currently developing within the **Mach 4** lifecycle—a system now operating with multi-tenant identity, cross-platform (Windows/Unix) compatibility, and polyglot persistence across three database engines.

*   **Twin-Track Ingestion:** Seamlessly pulls your planned *Intentions* from Google Calendar into a MongoDB landing zone, formats them, and merges them securely into the Neo4j Identity Graph.
*   **The 20-Second Recon Loop:** A lightning-fast, glassmorphic frontend UI designed for rapid verification of daily events, driving cognitive load to near-zero.
*   **Agentic Reflection:** Sophisticated CrewAI workflows spin up specialized autonomous agents (Socratic Coaches, GTKY Librarians, First-Serving Porter) to analyze the numeric delta ($\Delta$) between your Intent vs. Actuals, generating deep, non-critical insights.
*   **Sovereign Memory:** Every log, task, and reflection is saved as an interconnected node-pattern within a private Neo4j graph database, establishing a localized "digital brain." Vector embeddings are stored in Weaviate Cloud and ChromaDB for semantic search.
*   **Multi-Tenant Architecture:** All data operations are scoped to `user_email` via JWT middleware. No single-tenant hardcoding remains.

## Repository Architecture & Documentation

This repository relies on a sprawling ecosystem of agents and meticulous documentation. **If you are contributing, you MUST read the respective documentation.**

*   **[`src/`](src/):** The core intelligence engine containing:
    *   `app.py` — Flask application factory with 8 registered Blueprints
    *   `src/agents/` — Specialized Agent architectures (First-Serving Porter, Socratic Coach, GTKY Librarian)
    *   `src/database/` — Neo4j graph client, MongoDB storage, Weaviate/ChromaDB vector databases
    *   `src/integrations/` — Google Calendar API, GCP Compute, embedding clients
    *   `src/routes/` — Flask Blueprints for auth, journal, calendar, chat, inventory, admin, user
    *   `src/events/` — Redis-backed event publishing and worker processing
*   **[`frontend/`](frontend/):** The client-side application featuring Vanilla JS and Tailwind CSS v4 to drive the interactive Hero's Hub and Activity Dashboards.
*   **[`rag_system/`](rag_system/):** RAG pipeline for document ingestion and retrieval-augmented generation.
*   **[`Documentation/`](Documentation/):** The single source of truth for the project.
    *   **[`Documentation/Current_work/`](Documentation/Current_work/):** Contains `ACTIVE_*.md` tracker files mapping current development sprints.
    *   **[`Documentation/Future_work/`](Documentation/Future_work/):** Contains the `MACH4_beyond_ROADMAP.md` and `FUTURE_EXTENSIONS.md`.
    *   **[`Documentation/architecture/`](Documentation/architecture/):** Contains the definitive `AGENT_REGISTRY.md`, Neo4j `DATABASE_SCHEMA.md`, and the `SCRIPT_REGISTRY.md`.
    *   **[`.agent/rules/`](.agent/rules/):** The strict operational boundaries for any AI operating inside this repository.

## Setup & Installation

### 1. Zero-Trust Security Configuration (`.auth/`)
All environment variables, highly personal mappings, and Google OAuth tokens **must** be stored securely in an isolated `.auth/` directory at the project root. This directory is strictly `.gitignore`d.

Create `.auth/.env` and supply the following variables. **Use placeholder values as shown — never commit real secrets:**

```env
# --- Core Database Connections ---
NEO4J_URI="bolt://localhost:7687"             # Or your Neo4j Aura connection string
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="<your_neo4j_password>"
MONGO_URI="mongodb://localhost:27017/"         # Or your MongoDB Atlas connection string

# --- Authentication & Security ---
PORTER_API_KEY="<generate_a_random_api_key>"   # Used for admin endpoint auth
PORTER_ADMIN_KEY="<generate_a_random_key>"     # Used for admin route protection
JWT_SECRET="<generate_a_random_jwt_secret>"    # Used for JWT token signing
GOOGLE_CLIENT_USER_LOGIN_ID="<your_google_oauth_client_id>"
GOOGLE_CLIENT_USER_SECRET="<your_google_oauth_client_secret>"

# --- AI / LLM Providers ---
GROQ_API_KEY="<your_groq_api_key>"
# OPENAI_API_KEY="<your_openai_api_key>"       # Optional: for OpenAI-backed agents
# LANGCHAIN_API_KEY="<your_langsmith_key>"     # Optional: enables LangSmith tracing

# --- GCP Configuration ---
PROJECT_ID="<your_gcp_project_id>"
GOOGLE_CLOUD_REGION="us-central1"
GOOGLE_CLOUD_LOCATION="us-central1"

# --- Vector Database ---
# WEAVIATE_URL="<your_weaviate_cluster_url>"   # Optional: for Weaviate Cloud
# WEAVIATE_API_KEY="<your_weaviate_api_key>"   # Optional: for Weaviate Cloud

# --- Event System ---
# REDIS_URL="redis://localhost:6379/0"         # Optional: for Redis-backed event queue

# --- Admin Identity ---
NEXUS_ADMIN_EMAIL="<your_email@example.com>"
```

Ensure your `category_mapping.json` (as shown in `data/category_mapping.example.json`) is also placed in `.auth/`.

### 2. Environment & Dependencies
This project uses Python 3.12+. We manage Python dependencies using `uv` inside a Conda environment.

**Option A: Automatic Setup (via Makefile)**
```bash
make install
```

**Option B: Manual Setup**
```bash
conda create --name agentic_porter python=3.12 nodejs -y
conda activate agentic_porter
# Ensure uv is installed, then sync the dependencies
uv sync --dev
```

### 3. Running the Ecosystem

**Recommended: Docker (Production-like, cross-platform)**
```bash
make docker-build
make docker-run
```

**Development Mode (Local Flask server):**

*Terminal 1 (Backend API):*
```bash
make dev
# Or directly: conda run -n agentic_porter uv run python src/app.py
```

*Terminal 2 (Frontend):*
For local development, serve the frontend via a static file server or VS Code's Live Server extension pointed at `frontend/`.

> **Windows Development Note:** This project is actively developed on both Windows and Unix/Linux. The Makefile uses `ifeq ($(OS),Windows_NT)` branching for cross-platform targets. PowerShell equivalents of bash utility scripts are available in `scripts/analyze_scripts/`. See the Makefile for available `make` targets via `make help`.

### 4. Building Frontend Assets
```bash
make build-css
```
This compiles Tailwind CSS v4 from `frontend/css/input.css` to `frontend/css/style.css`.

## The Future: Mach 4 & Beyond

The **Mach 4** iteration focuses on advanced agent networking, multi-tenant architecture, and cross-platform development. Key upcoming features include the **First-Serving Porter** (a front-man manager outputting weighted daily recommendations), **Hub Progress Metrics**, and deep vector-semantic integration via Weaviate.

Read the full future breakdown in [`Documentation/Future_work/MACH4_beyond_ROADMAP.md`](Documentation/Future_work/MACH4_beyond_ROADMAP.md).