# Architectural Pivot (April 17, 2026)

> **Role Context:** Authored by Paul (Senior Principal Engineer and LLM/RAG Architect)
> **Priorities:** Sovereign Code, <20-second human friction rule, Neo4j graph relationships, MongoDB staging.

This document outlines the major architectural pivot for the Agentic Personal Porter project, addressing the structural, agentic, frontend, and observability layers following recent request loop crashes and scope modifications.

---

## 1. Data Infrastructure (MongoDB & Neo4j)

### Native MongoDB Time-Series Collections
To establish robust chronological tracking, we are integrating native MongoDB Time-Series collections. 

- **Calendar Ingestion Strategy:** We have implemented a sliding-window calendar ingestion process for both current and historical events. The ingestion script will manage batch pulls of current events and a rolling chronological fetch of historical events.
- **New Time-Series Collection Specification:**
  - **Collection Name:** `calendar_events_timeseries`
  - **Use Case:** Storing raw and processed calendar events optimized for temporal queries.
  - **Schema Considerations:** TimeField (`start_time`), MetaField (`event_type`, `pillar`), and measurements (`duration_minutes`).
- **Socratic Mirror Scope refinement:** The Mirror's integration with the data infrastructure is strictly pared down to categorizing Intention vs. Actual events across the defined 9 hero pillars.
- **Scalability & Rate-Limiting:** To handle high-frequency event ingestion by the `first_serving_porter`, we are introducing an exponential backoff queueing mechanism (e.g. Redis/Celery queue or strict batch-processing intervals) to buffer API calls to the LLM when processing hundreds of events.

---

## 2. Data Infrastructure: Vector Database Verification

- **Scale Beyond ChromaDB:** As the document parsing and historical logs verify ChromaDB "vibe checking" capabilities, verify production-grade Vector Database Weaviate for long term storage and accurate hybrid searching retrival.
- **Human Verification Imperative:** This migration will definitively require rigorous human-in-the-loop verification strategies to ensure that the shift in semantic storage does not corrupt or arbitrarily hallucinate the Hero's historical contexts.

---

## 3. Agent Roster Restructure

The agent roster for immediate development is being flattened and restructured to prevent hallucination looping and reduce cognitive load on the LLM orchestrators.

### The Categorizer (Formerly Socratic Mirror)
- **Scope Reduced:** Strict categorization of raw events into the 9 pillars.
- **Demotion:** Stripped of philosophical reasoning, it is now exclusively a lightning-fast, objective classifier pipeline.

### The Socratic Engine (Revived)
- **Deep 'Delta' Thinker:** Moved back from legacy storage into active duty. Analyzes the gap between "Intended Trajectory" and "Actual Execution" (Adventure Log style), exposing specifically the "Fog of War" missing timeline gaps.

### Audit Agent (NEW)
- **Role (The "Inspector"):** Audits the categorizations proposed by The Categorizer, flagging anomalous classifications (<70% confidence).
- **Friction Rule:** Feeds unverified events directly to the Hub's Verification Dashboard for 1-click approvals.

### The First-Serving Porter (Expanded Managerial Role)
- **Front-Man Manager:** Reads daily quotas and outputs definitive recommendations for filling gaps in the Hero's Identity Graph (`hero_origin.json`, `hero_ambition.json`).

### Time_Keeper (NEW)
- **Role (Temporal Specialist):** Dedicated to handling temporal queries by interrogating the Mongo Time-Series directly.

---

## 4. Frontend UI Pivot & Recent Developments (MACH 3 Scope Completion)

Over the course of the Mach 3 deployments, the frontend has been dramatically reconfigured:

- **Hub Verification Dashboard:** Added a dynamic verification UI highlighting unverified blocks, allowing "Approve All" routing or explicit drill-downs. 
- **Artifacts Grid Upgrade:** Migrated `/artifacts.html` from static rendering to a dynamic 1/3 grid. Now natively binds to `hero_origin`, `hero_ambition`, `hero_detriments`, and `category_mapping.json` directly from Sovereign Mongo representation. Includes active "architect focus" sidebars and collapsible elements tracking 16+ Epochs cleanly.
- **Journal Review Dashboard:** A powerful new Day-by-Day dashboard (`journal_review.html`) visually separating "Intentions" from "Actuals", explicitly rendering unstructured "Fog of War" timeline gaps to ensure high data hygiene.
- **Dynamic Learning Loop Pipeline:** Added `/api/journal/edit_event`. Now, if an event classification is corrected by the human on the Journal dashboard, the backend natively appends that specific string keyword to `category_mapping.json` via Python, training the Agentic Knowledge structures incrementally.
- **Bi-Directional Google Calendar Sync:** Explicit overwrite capabilities have been authored! `POST /api/calendar/push_to_gcal` allows the Agentic Porter (via the Journal Review UI) to securely execute destructive `service.events().update()` and `delete()` requests, cementing the local timeline as the definitive Source of Truth over the Google cloud.

---

## 5. Observability, Monitoring & Error Prevention

Following recent crashes caused by infinite requesting loops, heavy observability has been established.

### Tracing Collections
- **`first_serving_traces`:** A MongoDB collection logging every task delegation from the lead porter. Contains: `trace_id`, `target_agent`, `prompt`, `agent_state`, and `token_count`.
- **`first_serving_porter_happenings`:** Tracks behavioral heuristics of the First Porter.

### Execution Frameworks & Safeguards
- **LangSmith Integration:** A strict requirement for integrating LangSmith to observe mapping and looping bottlenecks visually.
- **Strict Exponential Backoff:** Mandatory implementation of exponential backoff decorators built cleanly around all LLM/Groq/OpenAI calls in the `get_` wrappers.
- **Request Density Strategy:** 
  - Implementation of local token tracking counters in memory that forcefully trips an error/halt circuit if > X tokens are consumed in < Y minutes by any solitary agent, severing infinite loops.
  - Implement max-retries on tool selections explicitly.

---

## 6. Verification Checklist (Post-Rest Audit)

Before pushing this architecture to full active production, the following rigorous verifications must be executed:

- [ ] **Bi-Directional Safety Audit:** Create a dummy event in Google Calendar, verify it propagates to Mongo, and test overwriting & deleting from the Journal Dashboard. Ensure NO live production historical events are accidentally wiped out by a bad API loop.
- [ ] **Socratic Engine Integrity Test:** Write a small script testing `SocraticMirrorEngine.calculate_daily_delta()` to ensure the arrays properly pair the Intention metrics alongside the Actuals without mismatching time zones.
- [ ] **Dynamic Knowledge Pipeline:** Reclassify an event in the Journal Review UI, then natively query `SovereignMongoStorage().get_hero_artifact('category_mapping.json')` to ensure the exact lowercase string correctly pushed into the `General` array of the respective target pillar.
- [ ] **Frontend Layout QA:** Check grid layouts on `/artifacts.html` and `/journal_review.html` on smaller screen resolutions (tablet view) to ensure the newly injected 1/3 and 1/2 responsive columns gracefully stack.
- [ ] **LangSmith Tripping:** Spin up a simulated hallucinating agent prompt. Verify that the agent halts itself upon hitting token saturation constraints natively via our new backoff structures. 
- [ ] **Weaviate Connectivity Check:** Ensure Weaviate instance is fully green-lit for RAG handoffs as we prepare to graduate from ChromaDB.
