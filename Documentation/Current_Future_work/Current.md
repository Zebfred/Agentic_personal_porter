# Current Development Directives: MACH 3.5

> [!NOTE]
> This document tracks high-priority actions and expectations for the MACH 3.5 architectural pivot. It serves as the definitive roadmap for review, validation, and improvement.

---

## 1. Data Infrastructure & Vector Memory
**Goal:** Establish a sovereign, high-performance foundation for historical tracking and semantic retrieval.

*   **Native MongoDB Time-Series:** 
    *   Deploy `calendar_events_timeseries` collection.
    *   Implement **Sliding-Window Ingestion** to handle batch pulls (current events) and rolling chronological fetches (historical data).
*   **Vector Verification:**
    *   Validate ChromaDB "vibe checking" for immediate semantic needs.
    *   Graduate to **Weaviate** for production-grade hybrid search.
    *   **Human-in-the-Loop:** Mandatory verification to ensure semantic shifts do not introduce context hallucinations.

---

## 2. Agent Roster Restructure
**Goal:** Flatten the agent hierarchy to prevent infinite loops and specialized error modes.

*   **Identity Architect (GTKY Agent):**
    *   Dedicated background scanner for Artifact Foundation (`hero_origin`, `hero_ambition`, `hero_detriments`).
    *   Identifies timeline gaps and generates concise interview questions.
    *   Wires `@tool update_artifact` and `scan_origin_story` to the First-Serving Porter.
*   **The Categorizer:**
    *   Rapid classification of raw events into the 9 Hero Pillars.
    *   Stripped of deep reasoning logic to ensure speed and objectivity.
*   **Audit Agent (The Inspector):**
    *   Audits Categorizer confidence levels (<70% flags).
    *   Drives the low-friction Verification Dashboard UI.
*   **Time_Keeper:**
    *   Temporal specialist agent querying the Mongo Time-Series directly.
*   **First-Serving Porter:**
    *   Central orchestrator and manager.
    *   Synthesizes Identity Architect findings into actionable daily recommendations.

---

## 3. Frontend & API Integration
**Goal:** Bridge backend logic to the Hub with a focus on the "<20-second human friction" rule.

*   **Hub Verification Dashboard:** 
    *   Directly inject "Pending Audits" UI into `index.html`.
    *   Support 1-click approvals for Audit Agent batches.
*   **Adventure-Calendar Upgrade:**
    *   New UI component for rolling monthly/weekly historical views.
*   **Journal Review Dashboard:**
    *   Source of Truth UI for deeper event modification and "Fog of War" gap identification.
*   **Supporting Endpoints:**
    *   `GET /api/artifacts/scan`: Exposes timeline gaps identified by Identity Architect.
    *   `GET /api/admin/unverified_audits`: Serves unverified batch records.
    *   `POST /api/admin/approve_audits`: Bulk approval processing.

---

## 4. Advanced Logic & Bi-Directional Sync
**Goal:** Empower agents to interact natively with external cloud services while maintaining local sovereignty.

*   **Socratic Mirror (Revitalized):**
    *   Deep "Delta" thinking between "Intended Trajectory" vs. "Actual Execution."
    *   Exposes discrepancies via `GET /api/journal/delta`.
*   **Bi-Directional GCal Sync:**
    *   `POST /api/calendar/push_to_gcal`: Allows the Porter to overwrite Google Calendar data based on local Journal Review edits (`update`/`delete`).
*   **Category Propagation:**
    *   Dynamic learning loop where manual human re-categorization natively updates `.auth/category_mapping.json`.

---

## 5. Observability & Stability
**Goal:** Prevent request explosions and infinite agent loops.

*   **Token Circuit Breaker:**
    *   Implement `TokenCircuitBreakerHandler` (LangChain Callback).
    *   Hard limit of **25,000 tokens** per execution sweep to sever rogue loops.
*   **LangSmith Integration:**
    *   Mandatory tracing for all multi-agent crew executions.
    *   Config assertion: `LANGCHAIN_TRACING_V2=true`.
*   **Monitoring Collections:**
    *   `first_serving_traces`: Log prompt, state, and token count.
    *   `first_serving_porter_happenings`: Track behavioral heuristics.

---

## Current Focus & Human Verification

### Immediate Tasks
- [ ] New frontend for the adventure log Month view.
- [ ] Active monitoring of First Serving agent behavior.
- [ ] Repair and sanitize `.auth/hero_detriments.json` (reformatting unquoted strings).

### Human noticed items of interest
- [ ] Misuse of local json objects over hero_artifacts collection from mongodb
- [] Proper automatic triggers/orchestration of the data pipeline does not seem to be properly in place yet
- [] Investigate the use and potential removal of the "Monthly History Calendar Overlay" currently hidden inside Adventure_Time_log.html
- [] Fixes to groq.APIError: tool call validation failed: attempted to call tool 'weaviate_hybrid_search {"pillar": "Career Goal", "query": "career development over last month"}' which was not in request.tools, which is monitoring for first_server
- [] some fixes to the Monthly log on how years,months and days are displayed, Do by a 4 week basis? So display should have 4 week of logs that can be displayed. Do that for a given "Month", regardless of the month

### Human thoughts of interest 
- [] Buildin an agent/model-based RL tool that can map out the Hero's potential life paths and the most optimal path for the Hero to take to achieve their goals and ambitions, the most likely path ( an in-between best outcome and realistic outcome given historic actions and choices), a worst case state ( a path that leads to the Hero's downfall or failure to achieve their goals and ambitions)


### Verification Checklist
- [ ] **Bi-Directional Safety Audit:** Verify dummy event GCal sync/overwrite without data loss.
- [ ] **Socratic Engine Integrity:** Validate `calculate_daily_delta()` array pairing.
- [ ] **Dynamic Knowledge Pipeline:** Confirm re-categorization pushes to `category_mapping.json`.
- [ ] **Frontend Layout QA:** Validate responsive stacking on mobile/tablet views for new grid components.
- [ ] **Circuit Breaker Trip Test:** Simulate hallucinating agent to confirm token saturation halt.

---

### Meta Development
- [x] **Establish Agentic Developer Rules:** Documented global rules for AI agents.
- [x] **Establish System Checks:** Formalized documentation and health check routine.

---

**High-Level Performance Goals:**
- **Analytic Depth:** Identify delta between Hero’s Intent and Actual actions at micro/macro levels.
- **Classification Accuracy:** Achieve >95% automated categorization for routine daily blocks.
- **Sovereign Growth:** Sustainable background harvesting of Origin and Ambition data.
- **User Friction:** Maintain all critical daily verifications within a <20-second window.
