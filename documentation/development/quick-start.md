# Quick Start Guide

## The Current State of the Application (Mach 4)

**IMPORTANT NOTE:** We have transitioned to a secure, Multi-Tenant architecture. All core features (Authentication, Google Calendar Sync, MongoDB Landing Zones, Neo4j Identity Graph Ingestion, and the RAG service query engine) are functional and partitioned by user email/credentials.

---

## 1. Zero-Trust Authentication Setup (Prerequisite)

Before running anything, you MUST establish the `.auth` quarantine directory at the root of the project to isolate sensitive credentials.

1. Create a folder named `.auth` in the project root.
2. Inside `.auth`, create a `.env` file containing the following configuration:
   ```env
   # API Keys & Security
   GROQ_API_KEY="your_groq_key"
   PORTER_API_KEY="your_admin_secret_key"
   JWT_SECRET="your_jwt_signing_secret"

   # Database Connections
   NEO4J_URI="bolt://localhost:7687"
   NEO4J_USERNAME="neo4j"
   NEO4J_PASSWORD="your_password"
   MONGO_URI="mongodb://localhost:27017/"

   # Google Cloud Configurations (for deployments/auth)
   PROJECT_ID="your_gcp_project_id"
   GOOGLE_CLOUD_REGION="us-central1"
   CORS_ORIGINS="http://localhost:5000,http://127.0.0.1:5000,http://localhost:5090,http://127.0.0.1:5090,http://localhost:6010,http://127.0.0.1:6010"
   ```
3. Place your Google API client `credentials.json` directly into the `.auth/` directory.

---

## 2. Diagnostics: Checking System Health

Always run the status check before attempting to boot the server to verify your database connections are live and dependencies are met.

Using the `Makefile` command:
```bash
make pulse
```
Or directly running the underlying python script:
```bash
python scripts/analyze_scripts/local_pulse_check.py
```
This script will formally verify that your Neo4j database is reachable, Python dependencies are met, and the `.auth` keys are properly positioned. It logs detailed JSON results to the `scripts/analyze_scripts/logs/` directory.

---

## 3. Running Locally (Development Mode)

We manage environments using **Conda** and dependencies via the **`uv`** package manager (defined in `pyproject.toml` and `uv.lock`).

### A. Environment & Dependency Installation
Create the environment and install all packages in dev mode using:
```bash
make install
```
*(This creates the `agentic_porter` conda environment with Python 3.12/NodeJS, and runs `uv sync --dev` to configure dependencies.)*

Alternatively, if you already have the environment and just need to sync packages:
```bash
conda activate agentic_porter
uv sync --dev
```

### B. Start the Backend API
To start the Flask development server:
```bash
make dev
```
Or run directly:
```bash
python src/app.py
```
*The Flask development server will spin up on port `5090` (configured for CORS and multi-tenant parsing).*

### C. Start the RAG Service
The RAG (Retrieval-Augmented Generation) query system runs as a FastAPI service on port `8000`. Start it locally via:
```bash
uvicorn rag_system.rag_service:app --host 0.0.0.0 --port 8000
```

### D. Start the Frontend UI
Open `frontend/index.html` via Visual Studio Code's **Live Server** extension (typically runs on `http://localhost:5500` or `http://localhost:3000`). Make sure your origin is allowed in the `.env`'s `CORS_ORIGINS`.

---

## 4. Running via Docker (Production Mode)

We containerize the Mach 4 production environment using `gunicorn` (for the backend API) and `docker-compose` (for the RAG service).

### A. Backend API Server (Port `6010`)
1. **Build the Docker Image:**
   ```bash
   make docker-build
   ```
   *(Or run: `docker build -t agentic-porter .`)*
2. **Run the Container:**
   ```bash
   make docker-run
   ```
   *(Or run: `docker run -p 6010:6010 --env-file .auth/.env -v $(pwd)/.auth:/app/.auth -v $(pwd)/data:/app/data -v ~/.config/gcloud:/root/.config/gcloud:ro agentic-porter`)*

### B. RAG Service (Port `8000`)
To launch the FastAPI query engine container:
```bash
docker compose up --build -d
```
The RAG production API will be exposed on `http://localhost:8000`.

---

## 5. Key URLs and Endpoints

### Backend API Server
- **Main API Root:** `http://localhost:5090` (Development) or `http://localhost:6010` (Docker/Production)
- **Process Journal (Reflections):** `POST /process_journal`
- **Fetch Calendar Events:** `GET /get_calendar_events?date=YYYY-MM-DD`
- **User Calendar Sync:** `POST /api/calendar/user_sync` (triggers full GCal -> Mongo -> Neo4j ingest pipeline)
- **Verification Dashboard Queue:** `GET /api/calendar/unverified_audits` & `POST /api/calendar/approve_audits` (accepts `gcal_ids` body)
- **Bi-Directional GCal Sync:** `POST /api/calendar/push_to_gcal` (supports `action: update` and `action: delete` directly on Google Calendar)
- **Fetch Inventory Details:** `GET /api/inventory`
- **Fetch/Save Artifacts:** `GET /api/artifacts/<artifact_name>` & `POST /api/artifacts/<artifact_name>` (where `<artifact_name>` is `hero_origin.json`, `hero_ambition.json`, `hero_detriments.json`, or `category_mapping.json`)
- **Scan Artifacts for Gaps:** `GET /api/artifacts/scan`
- **Graph Topology Data:** `GET /api/graph_data`

### RAG Service
- **Service API Root:** `http://localhost:8000`
- **Search Query Engine:** `POST /query` (accepts `{"query": "your question", "top_k": 5}`)
- **Health Heartbeat:** `GET /health`
- **Rebuild Vector Index:** `POST /rebuild_index` (triggers re-indexing of chunks from `data/` folder)
