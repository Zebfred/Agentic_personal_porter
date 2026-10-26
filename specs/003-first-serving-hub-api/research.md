# Phase 0 Research: First-Serving Agent API, Porter Hub Support & Jira/Jules Bridge GUI (`003-first-serving-hub-api`)

**Feature Branch**: `003-first-serving-hub-api`  
**Date**: 2026-10-25  
**Status**: Complete — All Technical Decisions Resolved

---

## 1. Hub Progress Metrics (`/api/user/hub_metrics`) & `events_to_be_classified` Staging Queue

### Decision
Implement `GET /api/user/hub_metrics` in `src/routes/user_routes.py` (and keep `GET /api/calendar/adventure_log` delegating to the same calculation helper for backward compatibility) backed by a dedicated MongoDB collection `MongoConfig.EVENTS_TO_BE_CLASSIFIED_COLLECTION = "events_to_be_classified"`.

### Rationale
- `frontend/index.html` renders 6 key telemetry counters (`#user-intentions-logged`, `#user-calendar-events`, `#user-events-classified`, `#user-matched-intentions`, `#user-valuable-detours`, `#user-detrimental-detours` + `#user-detrimental-delta`).
- Previously, `get_adventure_log()` hardcoded `"detrimental_delta": "↓ 0%"` and queried `raw_gcal_events` rather than a dedicated classification queue (`events_to_be_classified`).
- Adding `EVENTS_TO_BE_CLASSIFIED_COLLECTION = "events_to_be_classified"` with a compound index `(user_email, status, start_time DESCENDING)` and deterministic UUIDv5 (`UUIDGenerator.generate_for_event(gcal_id, user_email)`) ensures raw calendar events awaiting triage do not pollute Neo4j before confirmation.
- Week-over-week Detrimental Detour improvement is computed by comparing the count of `detrimental` detours in the current 7-day window (`[now - 7d, now]`) vs. the prior 7-day window (`[now - 14d, now - 7d]`), returning both a numeric percentage (`detrimental_improvement_pct`) and a formatted badge string (`detrimental_delta`, e.g., `"↓ 25%"`).

### Alternatives Considered
- **Querying Neo4j directly on every Hub load**: Rejected for latency and Bolt connection pool pressure; MongoDB indexed counts/projections return in `<5ms`.

---

## 2. One-Shot Weekly Planning Endpoint (`/api/planning`)

### Decision
Add `POST /api/planning` and `GET /api/planning` in `src/routes/journal_routes.py` (alongside existing `/api/planning/weekly`), accepting either a structured list of `WeeklyIntentionItem` blocks or a natural-language `expectation_text` string for a target `week_start_date`.

### Rationale
- When a Hero submits a full week's intentions in one shot (either from the Hub GUI or First-Serving Porter), `/api/planning` parses any bulleted/natural-language lines into structured `event_intentions` documents, assigns deterministic tenant-scoped UUIDs, and persists all intention documents in a single batched `bulk_write(ops, ordered=False)` call (`Bolt` compliance) while also updating `weekly_expectations` and merging into Neo4j (`:Hero)-[:EXPERIENCED]->(:Week)-[:PLANNED_AS]->(:Intention`).

---

## 3. Missing Artifact Discovery (`hero_origin.json` & `hero_ambition.json`)

### Decision
Enhance `GTKYIdentityArchitect` (`src/agents/gtky_identity_architect.py`) with `scan_missing_artifacts()` (and update `scan_for_missing_origin()` + `GET /api/artifacts/scan`) to inspect **both** `hero_origin.json` and `hero_ambition.json`, falling back to default schema templates when a new tenant has no stored artifact in MongoDB yet.

### Rationale
- Previously, `GTKYIdentityArchitect.scan_for_missing_origin()` only checked `hero_origin.json` and returned `"No origin story base found to scan."` when empty, ignoring `hero_ambition.json` (such as missing `primary_quest`, `yearly_milestones`, `core_pillars`, or `success_vision`).
- Returning both a structured `gaps` array (`ArtifactGapItem`) and the formatted markdown bullet list (`results`) preserves 100% compatibility with `frontend/js/user_hub.js` while satisfying `FR-005` and `SC-003`.

---

## 4. Historical Journal Review with Explicit `saga_status`

### Decision
Update `SovereignMongoStorage.save_freeform_journal()`, `get_journal_and_expectation_history()`, and `GET /api/journal/history` (`src/routes/journal_routes.py`) so every historical journal/expectation record includes a normalized `saga_status` (`RECEIVED`, `LLM_PROCESSING`, `GRAPH_INJECTED`, or `FAILED`) and optional linked Socratic `reflection` summary, and render the `saga_status` badge in `frontend/js/user_hub.js` and `frontend/js/journal_review.js`.

### Rationale
- `save_log` already recorded `saga_status.status`, whereas `save_freeform_journal` and `get_journal_and_expectation_history` omitted `saga_status`, leaving the UI unable to display whether an entry had finished pipeline processing.

---

## 5. Interactive Porter Hub GUI for the Jira ↔ Google Jules Bridge (`US4`)

### Decision
1. Add `GET /api/integrations/jira/status` in `src/routes/jira_routes.py` returning:
   - Active Spec-Kit feature metadata (`feature_id`, `tasks` parsed from `tasks.md` with inferred personas),
   - Tenant-scoped staged Jira issues from `jira_issues_staging` (projected with `{"_id": 0, ...}`),
   - Recent work orders from `jules_work_orders`,
   - Readiness indicators (`jira_configured: bool`, `jules_cli_available: bool`).
2. Add an interactive **Spec-Kit / Jira ↔ Google Jules Command Center** glassmorphic section to both `frontend/index.html` (Hero Hub) and `frontend/admin_index.html` (Nexus-Guild Admin Hub), wired in `frontend/js/user_hub.js` and `frontend/js/admin_hub.js`, plus a **One-Shot Weekly Planning** quick-entry card on `frontend/index.html`.

### Rationale
- Gives the user immediate, 1-click visual verification in the browser GUI (`http://localhost:5001/` and `/admin_index.html`) for Spec-Kit task parsing, Jira issue staging/syncing, persona assignment (`sentinel`, `bolt`, `palette`, `archie`, `docdoc`, `dave`, `crii`, `jovol`, `silas`), formatted Jules Work Order prompt previewing, and live Jules CLI dispatch—all adhering to the 20-Second Recon Loop ($\le 3$ clicks) and WCAG accessibility standards (`label for`, `aria-label`, async button loading states).
