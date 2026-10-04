# Core Functionality & Ongoing Work Review

**Date:** June 2026
**Reference Document:** `Porter_Project_Core_Functionality_and_Outstanding_Roadmap_2026_06.md`
**Active Trackers Reviewed:** `ACTIVE_BACKEND_TASKS.md`, `ACTIVE_AGENT_DEV.md`, `ACTIVE_FRONTEND_DEV.md`

## 1. Executive Summary

The project is currently transitioning from a single-tenant architecture to a multi-tenant, cloud-deployable ecosystem. The overarching goal is to achieve core application functionality with cost-effective agents (Vertex AI + Human-in-the-loop) and a stable First Serving Porter. 

While the architectural groundwork for multi-tenancy and raw data ingestion is largely complete (e.g., Silas Audit, Mongo Landing Zone), the **critical connective tissue**—specifically, how agents format data, how telemetry prevents infinite loops, and how the First-Serving agent interacts with the frontend—remains the primary bottleneck for achieving the core usability mandate.

Below is an analysis of the "Actionable Step-by-Step Priority Path" from the Roadmap compared against the active development trackers.

---

## 2. Roadmap Alignment & Ongoing Work

### Priority 1: Docker Container Deployment
**Roadmap Goal:** Complete Phase 1 of the container simulation to isolate cloud Gunicorn failures.
* **Backend Status (Pending):** `ACTIVE_BACKEND_TASKS.md` explicitly lists "Local Production Simulation" as an outstanding priority. The goal is to establish a rigorous local testing environment using the Dockerized Gunicorn setup to replicate server connection failures occurring on the cloud.
* **Progress:** The dynamic loading of `.auth/.env` has been verified, and Neo4j connection pooling has been optimized, but the endpoint stress testing and local Docker Gunicorn replication are still required.

### Priority 2: Setup `/Adventure_expectations` & Pipeline
**Roadmap Goal:** Build the database/endpoint pathways in Flask and Neo4j for unstructured intentions (replacing the old `/adventure_log`).
* **Frontend Status (Mixed):** The `Adventure_Time_log.html` migration is **Complete**. However, the flexible `Adventure-calendar` endpoint and UI component are still pending. 
* **Backend Status (Pending):** A dedicated `/api/planning` endpoint and the `events_to_be_classified` MongoDB collection need to be built to hold raw events that require agent/user triage before entering the Identity Graph.
* **Agent Status (Pending):** The First-Serving Porter needs to be connected to the Neo4j reader endpoint and its communication payload structure defined to properly handle these intentions.

### Priority 3: Format GTKY Outputs 
**Roadmap Goal:** Patch the LangGraph parsing rules to enable real data to write into `Porter_collections` (fixing the "dry-run" placeholder).
* **Agent Status (URGENT - Pending):** `ACTIVE_AGENT_DEV.md` flags this as URGENT. The `sync_calendar_to_graph` orchestrator is currently bypassing GTKY agents (Historian/Librarian) because they fail to return the precise schema required to write to `formatted_calendar_events`.
* **Backend Status (Pending):** The `formatted_calendar_events` collection logic is currently empty and needs to be fixed to pre-process raw GCal strings into structured, AI-ready JSON.
* **Agent Status (URGENT - Pending):** Multi-Tenant Context updates must be applied to all agent prompts to use `username` instead of hardcoded names like "Hero".

### Priority 4: Deploy Telemetry Traces
**Roadmap Goal:** Add Gunicorn execution logging to the MongoDB `first_serving_traces` collection to prevent infinite loops and manage API spend.
* **Backend Status (Pending):** Needs implementation of the `first_serving_traces` and `first_serving_porter_happenings` MongoDB collections. Token Request Density Monitoring is also pending to halt agents during request explosions.
* **Agent Status (Pending):** Integration of LangSmith (or equivalent) to trace crew execution and the implementation of exponential backoff decorators on LLM inference calls are outstanding.

---

## 3. Critical Gaps & Next Steps

Based on the cross-reference of active tasks, the following areas require immediate focus to achieve the core functionality:

1. **The GTKY Schema Fix (The Data Bottleneck):**
   * **The Issue:** Data is successfully landing in MongoDB, but the pipeline to Neo4j is stalled because the agents aren't outputting the correct JSON format. 
   * **Action:** Prioritize updating the Historian/Librarian prompts and parsing logic so events can transition from staging collections to Neo4j without the "dry-run" bypass.

2. **First-Serving Porter Integration (The Usability Bottleneck):**
   * **The Issue:** The frontend Verification Dashboard and Hub UI are largely scaffolded, but the backend API (`/api/user/hub_metrics`, Agent Chat Endpoint) and the First-Serving Agent's prompt/Neo4j connection are incomplete.
   * **Action:** Build the connective API routes and draft the system prompt for the First-Serving Porter so the user can actually interact with the new Hub.

3. **Telemetry & Stability (The FinOps Bottleneck):**
   * **The Issue:** Without `first_serving_traces` and exponential backoffs, the system is vulnerable to infinite loops that drain Vertex AI quotas.
   * **Action:** Implement the `first_serving_traces` collection and basic token density monitoring before deploying the First-Serving Porter to production.

4. **Multi-Tenant Context in Agents:**
   * **The Issue:** While the backend routes successfully use `user_email` and `username`, `ACTIVE_AGENT_DEV.md` notes that the agents still need their internal tracking and prompts updated to respect the multi-tenant `username`.
   * **Action:** Complete the username threading in `gtky_librarian.py` ingest methods and `audit_inspector.py`.
