# Google Calendar Sync Orchestration Analysis

This document outlines the current state of the backend orchestration and data pipelines for Google Calendar event ingestion, focusing on integration points with the `First-Serving Porter` and the overarching "Mach 3" architecture.

## 1. The Core Sync Pipeline (GCal → Mongo → Neo4j)

The core orchestration for filling events from Google Calendar is primarily driven by a 5-phase pipeline defined in `src/orchestrators/sync_calendar_to_graph.py`.

### The 5 Phases:
1. **Ingestion (Landing Zone)**
   - **Script:** `src/database/calendar_raw_sync_to_mongo.py`
   - **Action:** Pulls raw events from Google Calendar API and upserts them into the MongoDB `raw_calendar_events` collection with `sync_status = "staged"`.
   - **Mach 3 Dual-Write:** It also attempts a native time-series dual-write using `CalendarTimeseriesClient`.

2. **Classification (GTKY Librarian)**
   - **Script:** `src/orchestrators/sync_calendar_to_graph.py`
   - **Action:** Grabs "staged" events from MongoDB and passes them to the `GTKYLibrarian` agent for LLM-based classification in batches of 10.
   - **Output:** Transforms raw data into "Golden Objects."

3. **Staging (Formatted Zone)**
   - **Action:** Saves the "Golden Objects" back to MongoDB into the `formatted_calendar_events` collection. Updates the raw event's `sync_status` to `"formatted"`.

4. **Graph Injection (Neo4j)**
   - **Script:** `src/database/inject_hero_calendar.py` via `SovereignGraphInjector`
   - **Action:** Identifies formatted events that haven't hit the graph yet and injects them into the Neo4j Identity Graph using a Cypher `UNWIND` batch operation.

5. **Acknowledgment**
   - **Action:** Updates MongoDB to mark the events as `neo4j_synced` to prevent double-injection.

## 2. Integration with First-Serving Porter

The `First-Serving Porter` (defined in `src/agents/first_serving_porter.py`) acts as the Chief of Staff and orchestrator. It does not directly pull from Google Calendar but relies on downstream tools and agents that interact with the ingested data:

- **`fetch_unverified_audits` Tool:** Interacts with the `AuditInspector` to pull categorized events (Golden Objects) that the human hasn't verified yet (e.g., events with `sync_status` = "Pending" or "Staged").
- **`consult_time_keeper` Tool:** Engages the `TimeKeeperAgent` to query the temporal reality (what actually happened on a given day), which relies on the Mongo Time-Series collections populated by the dual-write in Phase 1.
- **`weaviate_hybrid_search` Tool:** Searches hybrid records in Weaviate for exact journal entries and calendar events mapped to the 9 life pillars.

## 3. Potential Breaks & "Mach 3" Bottlenecks

Based on the pipeline architecture and the Mach 3 intentions (Observability, Error Prevention, Loop Prevention), here are the likely areas where breaks occur:

1. **The GTKY Librarian Bottleneck (Phase 2):**
   - The Librarian processes events in chunks of 10 using an LLM (`llama-3.1-8b-instant`). If the LLM fails, times out, or hallucinates formatting, the events get stuck in the `staged` status and never reach Neo4j.
   - *Symptom:* `First-Serving Porter` can't "see" recent events because they never made it to the Identity Graph.

2. **Time-Series Dual-Write Failures:**
   - The ingestion script attempts a dual-write to the new Mach 3 Mongo Time-Series collections (`CalendarTimeseriesClient`). If this fails silently or has schema mismatches, the `TimeKeeperAgent` (used by First-Serving Porter) will return empty or hallucinated summaries.

3. **Audit/Verification Disconnect:**
   - The pipeline creates "Golden Objects" that require human verification via the Verification Dashboard. If the `AuditInspector` logic is flawed or the UI fails to update the verification status, events might remain in a "limbo" state.

4. **Token Limits & Circuit Breakers:**
   - The `First-Serving Porter` has a `TokenCircuitBreakerHandler` (max 25,000 tokens). If it loops while trying to extract information from `consult_time_keeper` or `fetch_unverified_audits`, it will trip the breaker and halt, leading to the "systemic logic loop" error in the UI.
