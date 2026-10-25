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
    *   `app.py` — Flask application factory with 9 registered Blueprints
    *   `src/agents/` — Specialized Agent architectures (First-Serving Porter, Socratic Coach, GTKY Librarian)
    *   `src/database/` — Neo4j graph client, MongoDB storage (`mongomock` local TDD support), Weaviate/ChromaDB vector databases
    *   `src/integrations/` — Google Calendar API, Atlassian Jira REST v3 client (`jira_client.py`), Google Jules CLI dispatcher (`jules_dispatcher.py`), GCP Compute, embedding clients
    *   `src/orchestrators/` — Spec-Kit ↔ Jira/Jules bridge orchestrator (`speckit_jira_bridge.py`)
    *   `src/routes/` — Flask Blueprints for auth, journal, calendar, chat, inventory, admin, user, and Jira/Jules integrations
    *   `src/schemas/` — Contract-first Pydantic v2 boundary schemas (`api_models.py`, `jira_models.py`)
    *   `src/events/` — Redis-backed event publishing and worker processing
*   **[`frontend/`](frontend/):** The client-side application featuring Vanilla JS and Tailwind CSS v4 to drive the interactive Hero's Hub and Activity Dashboards.
*   **[`rag_system/`](rag_system/):** RAG pipeline for document ingestion and retrieval-augmented generation.
*   **[`specs/`](specs/):** Spec-Kit feature specifications, plans, data models, contracts, and task breakdowns (`001-evaluate-project-state`, `002-jira-jules-bridge`, `003-first-serving-hub-api`).
*   **[`.agents/`](.agents/) & [`.jules/`](.jules/):** Cross-surface agent configurations:
    *   **[`.agents/agents/`](.agents/agents/):** The 12 True CLI Agent definitions (`silas`, `sentinel`, `bolt`, `palette`, `archie`, `docdoc`, `dave`, `crii`, `jovol`, `backend-porter`, `frontend-porter`, `agentic-porter`).
    *   **[`.agents/rules/`](.agents/rules/):** Strict operational boundaries and protocols (`rules.md`, `Fiona_protocol.md`, `silas_protocol.md`).
    *   **[`.jules/`](.jules/):** Chronological agent activity logs and operational playbooks.
*   **[`documentation/`](documentation/):** The single source of truth for the project (strictly lowercase `kebab-case.md`).
    *   **[`documentation/current-work/`](documentation/current-work/):** Contains `active-*.md` tracker files (`active-backend-tasks.md`, `active-frontend-dev.md`, `active-agent-dev.md`).
    *   **[`documentation/future-work/`](documentation/future-work/):** Contains `mach4-beyond-roadmap.md`, `future-extensions.md`, and `local-ollama-routing-blueprint.md`.
    *   **[`documentation/architecture/`](documentation/architecture/):** Contains [`spec-kit-constitution.md`](documentation/architecture/spec-kit-constitution.md), [`agent-roster.md`](documentation/architecture/agent-roster.md), [`cli-agents-guide.md`](documentation/architecture/cli-agents-guide.md), [`jules-cli-runbook.md`](documentation/architecture/jules-cli-runbook.md), [`agent-registry.md`](documentation/architecture/agent-registry.md), Neo4j [`database-schema.md`](documentation/architecture/database-schema.md), and [`script-registry.md`](documentation/architecture/script-registry.md).

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

# --- Optional: Atlassian Jira & Google Jules Bridge ---
# JIRA_BASE_URL="https://your-org.atlassian.net"
# JIRA_EMAIL="<your_jira_email@example.com>"
# JIRA_API_TOKEN="<your_atlassian_api_token>"
# JIRA_PROJECT_KEY="PORTER"
```

Ensure your `category_mapping.json` (as shown in `data/category_mapping.example.json`) is also placed in `.auth/`.

### 2. Environment & Dependencies
This project targets **Python 3.12–3.14** and uses **`uv`** (`pyproject.toml` + `uv.lock`) exclusively for fast, reproducible virtual environment and dependency management (`.venv`).

**Option A: Automatic Setup (via Makefile)**
```bash
make install
```

**Option B: Direct `uv` Setup**
```bash
uv sync --extra dev
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
# Or directly: uv run python src/app.py
```

*Terminal 2 (Frontend):*
For local development, serve the frontend via a static file server or VS Code's Live Server extension pointed at `frontend/`.

> **Cross-Platform Development Note:** This project is actively developed on both Windows and Linux. Standardized Git hooks in `.githooks/` (`scripts/git_hooks_runner.py`) and `Makefile` targets run seamlessly across both OS environments. Run `make help` to view all available targets.

### 4. Building Frontend Assets
```bash
make build-css
```
This compiles Tailwind CSS v4 from `frontend/css/input.css` to `frontend/css/style.css`.

### 5. Verification Gates, Spec-Kit & True CLI Agents
```bash
# Push-button Silas Definition-of-Done Gate (DocDoc, Ruff, Mypy, Pytest unit suite)
make verify-done

# Execute all 8 specialized quality persona checks (Sentinel, Bolt, Palette, Archie, DocDoc, Dave, Crii, Jovol)
make test-roster

# Preview or push Spec-Kit tasks.md to Atlassian Jira & format Google Jules work orders
make sync-jira
make jules-dispatch
```

## The Future: Mach 4 & Beyond

The **Mach 4** iteration focuses on advanced agent networking, Spec-Kit governance, multi-tenant architecture, and hybrid local/cloud inference. Key active and upcoming features include the **First-Serving Porter Hub API (`003-first-serving-hub-api`)**, **Hub Progress Metrics**, **Local Ollama SLM Triage**, and deep vector-semantic integration via Weaviate.

Read the full future breakdown in [`documentation/future-work/mach4-beyond-roadmap.md`](documentation/future-work/mach4-beyond-roadmap.md) and [`documentation/future-work/local-ollama-routing-blueprint.md`](documentation/future-work/local-ollama-routing-blueprint.md).