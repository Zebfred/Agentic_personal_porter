# Active Backend Development

This document tracks immediate, high-priority tasks for the Python backend infrastructure (`app.py`, agent pipelines, data ingestion, and cloud deployments).

## Priority: First-Serving Agent API & Hub Support
*Status: Requirements drafted in ACTIVE_AGENT_DEV.md*

- [ ] **Agent Chat Endpoint:** Create a secure WebSocket or POST route to handle real-time conversations with the First-Serving Porter on the new Hub.
- [ ] **Graph Metric Endpoints:** Build endpoints that explicitly query Neo4j for high-level progress metrics to populate the Hub dashboard.
- [ ] **Missing Artifact Queries:** Build logic allowing the First-Serving agent to query `hero_origin.json` and `hero_ambition.json` for empty fields and prompt the user.
- [ ] **Historical Journal API:** Create an endpoint to serve historical journal records and LLM reflections for the new `journal_review.html` UI.

## Highest Priority: Server Networking & Cloud Deployment Fixes
*Status: Investigating structural connection issues for production.*

- [ ] **Local Production Simulation:** Establish a rigorous local testing environment (using the Dockerized Gunicorn setup) to replicate and isolate the exact server connection failures occurring on the cloud production instance.
- [ ] **Resolve Neo4j/Cloud Networking:** Fix the `Cannot resolve address 402abe07.databases.neo4j.io:7687` connection failure or dynamic environment variable mounting issues causing the server to detach from the graph database in production.
- [ ] **API Endpoint Stress Testing:** Validate all heavily utilized endpoints (`/process_journal`, `/get_calendar_events`) for resilience against dropped connections or timeouts during large LLM inference runs.

## Secondary Priority: Twin-Track Data Ingestion (Mach 2)
*Status: Architecture mapped, pipelines verified.*

- [x] **Mongo Landing Zone:** Finalize the script/pipeline for pulling daily bulk logs from Google Calendar directly into a MongoDB cluster. *(Verified: Landing zone fully functional with 13.5k events.)*
- [x] **Format & Clean Pipeline:** Pre-process the raw GCal strings into structured, AI-ready JSON strictly inside the Mongo landing zone before it ever touches the primary identity graph. *(Verified: Formatting pipeline processes correctly via `mongo_storage`.)*
- [x] **Neo4j Merge Validation:** Ensure the `MERGE` logic pushing from Mongo to Neo4j is rigorously idempotent. Test it against massive historical JSON samples to guarantee repeated syncs never degrade the graph or create duplicate "ghost" relationships. *(Verified: Idempotent using `gcal_id` constraints.)*

## Tertiary Priority: Agent Socratic Upgrades & Backups (Mach 2)
*Status: Completed upgrades & backup scripts scripts.*

- [x] **Socratic Prompt Expansion:** Upgrade the reflection agent's system prompt to intelligently detect "The Fog of War" (untracked hours) and differentiate between "Restorative Rest" (positive) vs. "Mindless Stagnation" (negative). *(Verified: Added gap calculations algorithm and prompt parsing).*
- [x] **Database Snapshots:** Set up automated cron-jobs or scripts ensuring regular, secure Neo4j graph exports to prevent catastrophic data loss during turbulent development phases. *(Verified: Created locally in `helper_scripts/neo4j_snapshot.py`).*

## Cloud Operations (Mach 2)
*Status: Architecture defined.*

- [ ] **Cloud Cron Setup:** Configure a Cloud Scheduler (e.g., GCP Cloud Scheduler) to trigger automatic syncs. The scheduler must be configured to send an HTTP POST request to `/api/admin/sync_calendar` on a regular cadence, authenticated using the `Authorization: Bearer <PORTER_API_KEY>` header. No additional python development is required inside the container, as the endpoint is already built.
- [x] **Dynamic Cloud Deployment:** Simplified `deploy_gcp.sh` to dynamically load all environment variables from `.auth/.env` instead of manual instantiation. *(Verified: Dynamic parsing logic implemented and tested.)*

## Priority: Artifacts & Inventory API Support
*Status: Severe file-naming collisions identified, API endpoints failing.*

- [x] **Artifact Naming Standardization:** Standardized across the backend to `hero_origin.json`, `hero_ambition.json`, and `hero_detriments.json`.
- [x] **Artifacts API:** Debugged and verified. Standardized pathing to `.auth/` for detriments and `data/hero_artifacts/` for origins/ambitions.
- [x] **Inventory API:** Debugged and verified. Payload format correctly matches `script.js` expectations.

## Priority: Database Architecture & Ecosystem Verification
*Status: Planning phase for long-term storage and connection integrity.*

- [ ] **Vector Database Integration:** Set up a proper production vector database (MongoDB Atlas Vector Search setup in `vector_storage.py`) that the Corrector and GTKY agents will interact with for long-term semantic search and massive document storage.
- [ ] **Mongo Time-Series Logging:** Update our MongoDB-related scripts to automatically pull from the calendar via `calendar_timeseries.py`, progressing further back in time, and establishing a robust time-series connection for historical data. The backend logic is now shifted to cleanly divide events into `raw_gcal_timeseries`, `event_intentions`, `event_actuals`, and `unified_events` using a consistent event UUID.
- [ ] **Backend Auditing Pipeline:** Implement proper backend auditing logic strictly based on the frontend journal reflections to ensure reflections are cleanly digested by the agents.
- [ ] **Neo4j Structural Verification:** Run verification checks to confirm the Identity Graph structure perfectly matches our intended schema models.
- [ ] **Frontend-to-Backend End-to-End Validation:** Rigorously verify that the new frontend UI elements we are working with right now are correctly routing to and triggering the backend endpoints.

# Active Backend Tasks

This document tracks backend development tasks, architectural shifts, and long-term storage requirements for the Agentic Personal Porter application.

## Long-Term Memory Storage (Vector DB)
- **Objective:** Integrate a Vector Database to serve as long-term memory for the Agentic Porter Ecosystem.
- **Optimization (IVF/PQ Clustering):** Implement Inverted File Index (IVF) and Product Quantization (PQ) to aggressively compress vectors and restrict the memory footprint to the 1GB budget.
- **Context:** Currently, we rely on Neo4j for semantic Identity Graph relationships and MongoDB for raw time-series data. However, as the user interacts via chat (the First-Serving Porter), retaining unstructured semantic memory over extended periods requires vector similarity embeddings.
- **Status:** Planning Phase. This will be tackled in a future session after the initial Agent drafts are finalized.

## MongoDB Time Series & Migration
- **Objective:** Migrate JSON configuration architectures like `hero_ambition.json` and `hero_origin.json` to MongoDB while implementing formal Time Series Collections for calendar data.
- **Intent-Actual Schema:** Refactor calendar ingestion to produce a unified `Intent-Actual` JSON document. This allows a single query to calculate the "Delta" (alignment score) natively.
- **Summarization Echelons:** Do not store full text recursively. Store Echelon 1 (Daily details), Echelon 2 (Weekly Agent Recaps), and Echelon 3 (Monthly 'Hero Numbers').
- **Status:** Pending implementation.

## Integration of New Agents
- **Objective:** Expand the agent capabilities in the backend and ensure they share the same LLM primitives.
- **Frameworks:** We are operating a dual-framework setup where CrewAI is utilized for intensive, batch, multi-agent synchronized executions (e.g. daily Socratic Mirror reflections) and LangChain generic agents handle low-latency direct user-chat interactions (e.g., First-Serving Porter).

## Neo4j Optimizations & Pulse Architecture
- **Objective:** Transition to a "Scheduled Heartbeat" batching strategy to reduce continuous high-friction writing to the Graph database.
- **Sovereign Self-Hosting:** Explore moving Neo4j to a Sovereign GCP Compute Engine Docker container to keep data internal and eliminate node limits (est. $7-$15/month).
- **The Pulse (Orchestrator):** Configure the system to only "Wake Up" the graph database during a scheduled pulse (e.g., 8:00 AM and 10:00 PM).
- **Batch Logic Requirements:**
  - [ ] **Phase 1 (Accumulate):** Ensure GCal events accumulate efficiently in the MongoDB Landing Zone throughout the day.
  - [ ] **Phase 2 (Classify):** Automate the "GTKY Librarian" agent to pull the daily batch, classify events against Hero Artifacts, and mint "Golden Objects."
  - [ ] **Phase 3 (Merge):** Implement a single UNWIND Cypher transaction in Python to inject the entire day's batch in under 5 seconds.