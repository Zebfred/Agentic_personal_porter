# Quick Start Guide

## The Current State of the Application (Mach 2)

**IMPORTANT NOTE:** We are actively transitioning into the completed Mach 2 architecture. While many backend agent pipelines are completed, **the server connection and automated "Twin-Track" ingestion (Google Calendar -> Mongo -> Neo4j) are actively being wired in and are not fully functional end-to-end via the UI yet.** 

However, you can still boot the server, run the frontend, and utilize the diagnostic scripts.

---

## 1. Zero-Trust Authentication Setup (Prerequisite)

Before running anything, you MUST establish the `.auth` quarantine directory.

1. Create a folder named `.auth` in the project root.
2. Inside `.auth`, create a `.env` file with the following:
   ```env
   GROQ_API_KEY="your_groq_key"
   NEO4J_URI="bolt://localhost:7687"
   NEO4J_USERNAME="neo4j"
   NEO4J_PASSWORD="your_password"
   MONGO_URI="mongodb://localhost:27017/"
   ```
3. Place your Google API `credentials.json` directly into the `.auth/` directory.

---

## 2. Diagnostics: Checking System Health

Always run the status check before attempting to boot the server to verify your `.auth` paths and database connections are live.

```bash
python helper_scripts/check_status.py
```
This script will formally verify that your Neo4j database is reachable, Python dependencies are met, and the `.auth` keys are properly positioned.

---

## 3. Running Locally (Development Mode)

1. **Activate Environment:** Ensure your conda environment or virtualenv is active.
   ```bash
   conda activate agentic_porter
   pip install -r requirements.txt
   ```
2. **Start the Backend API:**
   ```bash
   python src/app.py
   ```
   *The Flask dev server will spin up on port 5000.*

3. **Start the Frontend UI:**
   Open `frontend/index.html` via Visual Studio Code's **Live Server** extension.

---

## 4. Running via Docker (Production Mode)

We have containerized the Mach 2 environment utilizing Gunicorn. 

1. **Build the Docker Image:**
   ```bash
   docker build -t agentic-porter:mach2 .
   ```
2. **Run the Container:**
   ```bash
   docker run -d \
     --name porter_server \
     -p 5090:5090 \
     -v $(pwd)/.auth:/app/.auth \
     -v $(pwd)/logs:/app/logs \
     agentic-porter:mach2
   ```
   *Note: We dynamically mount the `.auth` directory so your sensitive keys are never baked directly into the Docker image.*

3. **Access the Application:** The production server will be exposed on `http://localhost:5090`.

---

## 5. Key URLs and Endpoints

### Backend Server (`app.py`)
- Main API Root: `http://localhost:5000` (or `5090` via Docker)
- Process Journal: `POST /process_journal`
- Fetch Events: `GET /get_calendar_events?date=2026-03-24`
- Hero Artifacts: `GET /artifacts/hero_origin`

### Administrative Maintenance Endpoints (Work-In-Progress)
- Sync Calendar to Graph: `POST /admin/sync_calendar`
- Inject Foundation: `POST /admin/inject_foundation`
