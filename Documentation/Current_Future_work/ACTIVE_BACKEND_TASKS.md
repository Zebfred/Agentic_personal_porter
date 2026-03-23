# Active Backend Development

This document tracks immediate, high-priority tasks for the Python backend infrastructure (`app.py`, agent pipelines, data ingestion, and cloud deployments).

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

- [ ] **Cloud Cron Setup:** Configure a Cloud Scheduler (e.g., GCP Cloud Scheduler or AWS EventBridge) to trigger automatic syncs. The scheduler must be configured to send an HTTP POST request to `/api/admin/sync_calendar` on a regular cadence, authenticated using the `Authorization: Bearer <PORTER_API_KEY>` header. No additional python development is required inside the container, as the endpoint is already built.

## Priority: Artifacts & Inventory API Support
*Status: Investigating why frontend endpoints are non-functional.*

- [ ] **Artifacts API:** Debug the `GET` and `POST` routes for `/api/artifacts/<artifact_name>` to ensure JSON data is being properly fetched and saved without permissions or pathing errors.
- [ ] **Inventory API:** Debug `GET /api/inventory` to ensure the payload format correctly matches what `script.js` expects to render the glassmorphic grid.

Updating our mongo related scripts to be able to pull automatically from the calendar in progressing further back in time. 
Being able to pull the data and store in a time series connection
Setting up a proper vector database for production and long term storage.