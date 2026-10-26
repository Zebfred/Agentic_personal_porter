# Feature Specification: First-Serving Agent API & Porter Hub Support

**Feature Branch**: `003-first-serving-hub-api`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Priority: First-Serving Agent API & Hub Support — Agent Chat Endpoint, Weekly Planning Endpoint (/api/planning), Events Classification Queue (events_to_be_classified), Hub Progress Metrics API (/api/user/hub_metrics), Missing Artifact Queries (hero_origin.json & hero_ambition.json), and Historical Journal API with saga_status."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hub Progress Metrics & Event Classification Queue (Priority: P1)

As an authenticated Hero visiting the Porter Hub dashboard, I want to view my real-time weekly progress metrics—including Intentions Logged, Calendar Events Logged, Events to be Classified, Matched Intentions, Valuable Detours, and week-over-week Detrimental Detour improvements—and inspect or triage unclassified calendar events waiting in a dedicated staging queue before they enter my permanent Identity Graph.

**Why this priority**: Provides the foundational visibility and data staging layer required by the Porter Hub dashboard and the 20-Second Recon Loop, ensuring raw calendar events do not pollute the Identity Graph before triage.

**Independent Test**: Can be fully tested by seeding tenant-scoped intention, actual, and unclassified event records for two consecutive weeks, querying the Hub Progress Metrics endpoint and Classification Queue, and verifying exact metric calculations and strict tenant isolation.

**Acceptance Scenarios**:

1. **Given** an authenticated Hero with logged intentions, actual events, and unclassified calendar items across the current and previous 7-day windows, **When** the Hero loads the Porter Hub metrics view, **Then** the system returns accurate counts for Intentions Logged, Calendar Events Logged, Events to be Classified, Matched Intentions, Valuable Detours, and the week-over-week percentage/count improvement in Detrimental Detours.
2. **Given** raw calendar events ingested for a Hero that lack confirmed category or intention alignment, **When** those events are staged for triage, **Then** they are stored in the dedicated classification queue scoped to the Hero's identity until confirmed or classified.
3. **Given** two different authenticated Heroes, **When** either Hero queries Hub metrics or the classification queue, **Then** zero records or metrics from the other Hero are ever included in the response.

---

### User Story 2 - First-Serving Porter Chat, Missing Artifact Discovery & One-Shot Weekly Planning (Priority: P2)

As an authenticated Hero interacting with the First-Serving Porter on the Hub, I want to hold context-aware conversations that proactively identify missing fields in my Origin Story and Ambition profiles, and submit a full week's worth of high-level intentions in a single planning interaction, so that my identity profile and weekly plan stay complete with minimal friction.

**Why this priority**: Powers the core interactive loop of the First-Serving Porter on the Hub—onboarding incomplete Hero profiles and translating natural-language weekly goals into structured intentions in one shot.

**Independent Test**: Can be independently tested by invoking the First-Serving chat and weekly planning flows for a tenant with partially empty origin/ambition artifacts and a natural-language weekly plan, verifying that missing artifact prompts are surfaced and structured weekly intentions are persisted in a single batch.

**Acceptance Scenarios**:

1. **Given** an authenticated Hero whose Origin Story or Ambition profile contains unpopulated fields, **When** the Hero initiates or continues a session with the First-Serving Porter, **Then** the agent detects the missing profile attributes and naturally prompts the Hero to fill one gap at a time.
2. **Given** an authenticated Hero planning their upcoming week, **When** the Hero submits a full week's worth of general intentions in one shot via the Weekly Planning flow, **Then** the system parses, validates, and batch-persists the structured weekly intentions scoped to the Hero's identity.
3. **Given** a real-time message sent to the First-Serving Porter from the Hub, **When** the request is processed, **Then** the conversation history, trace telemetry, and identity updates remain strictly bound to the authenticated Hero's email identity.

---

### User Story 3 - Historical Journal Review & Saga Status Tracking (Priority: P3)

As an authenticated Hero reviewing past journal entries and Socratic reflections on the Journal Review screen, I want to browse my chronological journal records alongside their generated reflections and real-time processing status (`RECEIVED`, `LLM_PROCESSING`, `GRAPH_INJECTED`, `FAILED`), so that I can track my personal growth over time and immediately see whether an entry has finished graph synchronization.

**Why this priority**: Completes the end-to-end reflection loop for the `journal_review.html` interface and surfaces pipeline reliability via explicit saga state tracking.

**Independent Test**: Can be independently tested by creating tenant-scoped journal records across multiple dates and saga states (`RECEIVED`, `LLM_PROCESSING`, `GRAPH_INJECTED`, `FAILED`) and querying the historical journal review endpoint to verify chronological ordering, pagination/filtering, and accurate `saga_status` reporting.

**Acceptance Scenarios**:

1. **Given** an authenticated Hero with historical journal entries and reflections, **When** the Hero opens the Historical Journal Review view, **Then** the system returns the Hero's journal entries in reverse-chronological order including reflection insights and each entry's current `saga_status`.
2. **Given** a journal entry currently undergoing reflection analysis or graph persistence, **When** the processing pipeline transitions states, **Then** the entry's `saga_status` updates accurately from `RECEIVED` to `LLM_PROCESSING` and finally to `GRAPH_INJECTED` (or `FAILED` with a sanitized reason).

---

### User Story 4 - Interactive Porter Hub GUI for Jira ↔ Google Jules Bridge & Live Browser Verification (Priority: P1)

As an authenticated Hero or Nexus-Guild Admin using the Porter Hub browser interface (`index.html` and `admin_index.html`), I want a dedicated **Spec-Kit / Jira ↔ Google Jules Command Center** widget in the GUI—alongside live Hub Progress Metrics, One-Shot Weekly Planning, and Missing Artifact Scans—so that I can visually inspect Spec-Kit feature tasks (`T001`+), trigger Jira synchronization, preview formatted Jules Work Orders (with `.agents/roster/<persona>.md` rules), and dispatch tasks to Google Jules directly from the browser without relying solely on terminal CLI commands.

**Why this priority**: Bridges the gap between backend/CLI readiness and interactive visual verification in the browser GUI, making both `002-jira-jules-bridge` and `003-first-serving-hub-api` immediately visible, testable, and actionable from the Porter Hub dashboard.

**Independent Test**: Can be independently tested by opening the Porter Hub GUI (`/` or `/admin_index`), loading the Jira ↔ Jules Bridge status endpoint (`GET /api/integrations/jira/status`), clicking "Push Spec-Kit Tasks", selecting a task (e.g., `T001`), clicking "Preview Jules Work Order" to inspect the generated prompt in the GUI, and clicking "Dispatch to Jules".

**Acceptance Scenarios**:

1. **Given** an authenticated user on the Porter Hub (`index.html` or `admin_index.html`), **When** the dashboard loads, **Then** the **Jira ↔ Google Jules Command Center** panel displays the active Spec-Kit feature ID, parsed `tasks.md` items with inferred persona badges (`sentinel`, `bolt`, `palette`, `archie`, `docdoc`, `dave`, `crii`, `jovol`, `silas`), staged Jira ticket statuses, and recent Jules work orders via `GET /api/integrations/jira/status`.
2. **Given** an authenticated user viewing the Command Center panel in the browser GUI, **When** the user selects a task and clicks **Preview Work Order** or **Dispatch to Jules**, **Then** the GUI invokes `POST /api/integrations/jules/dispatch` and renders the formatted `JulesWorkOrder` prompt (including `.agents/roster/<persona>.md` directives and verification gates) and session status directly in the browser.
3. **Given** an authenticated user on the Porter Hub (`index.html`), **When** the user submits a one-shot weekly intention plan or views Hub Progress Metrics, **Then** the GUI calls `/api/planning` and `/api/user/hub_metrics` and immediately refreshes the rendered dashboard counters without a full page reload.

---

### Edge Cases

- **New Tenant with Zero Historical Data**: What happens when a newly registered Hero requests Hub Progress Metrics or Historical Journals? The system must return zeroed metric counters (with `0.0` week-over-week detour delta) and an empty journal list rather than raising division-by-zero or missing-collection errors.
- **Missing or Uninitialized Origin/Ambition Artifacts**: What happens when `hero_origin.json` or `hero_ambition.json` does not yet exist for a tenant? The system must gracefully fall back to the default template structure, treating all template fields as empty candidates for First-Serving Porter discovery.
- **Duplicate Unclassified Events**: What happens when the same calendar event is queued for classification multiple times? The classification queue must deduplicate records using deterministic tenant-scoped event UUIDs (`user_email` + `gcal_id`).
- **Transient LLM Provider Failure During Weekly Planning or Chat**: What happens when the primary model provider is rate-limited or unreachable? The system must invoke the resilient fallback chain or return a sanitized, actionable status while preserving the user's raw input.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a tenant-scoped First-Serving Porter chat endpoint that processes conversational turns, enforces JWT `user_email` isolation, and records delegation trace telemetry.
- **FR-002**: System MUST provide a Weekly Planning endpoint (`/api/planning`) that accepts a Hero's natural-language or structured weekly intentions and persists the resulting week of intention records in a single batched operation.
- **FR-003**: System MUST maintain a dedicated staging collection (`events_to_be_classified`) for raw calendar events awaiting agent or Hero triage prior to Identity Graph injection, keyed by deterministic tenant-scoped UUIDs.
- **FR-004**: System MUST provide a Hub Progress Metrics endpoint (`/api/user/hub_metrics`) that calculates and returns: *Intentions Logged*, *Calendar Events Logged*, *Events to be Classified*, *Matched Intentions*, *Valuable Detours*, and *week-over-week Detrimental Detour improvements* for the authenticated Hero.
- **FR-005**: System MUST provide missing-artifact discovery logic enabling the First-Serving Porter to inspect a Hero's `hero_origin.json` and `hero_ambition.json` profiles for empty or unpopulated fields and generate targeted onboarding prompts.
- **FR-006**: System MUST provide a Historical Journal endpoint that returns reverse-chronological journal records, Socratic reflections, and explicit `saga_status` (`RECEIVED`, `LLM_PROCESSING`, `GRAPH_INJECTED`, `FAILED`) for the `journal_review.html` interface.
- **FR-007**: All database reads and writes across the Hub metrics, classification queue, weekly planning, and journal review flows MUST use explicit field projections and batched `bulk_write` operations where multiple records are persisted.
- **FR-008**: System MUST provide a `GET /api/integrations/jira/status` endpoint returning the active Spec-Kit feature's parsed tasks, tenant-scoped staged Jira issues (`jira_issues_staging`), recent `jules_work_orders`, and credential/CLI readiness flags for the Hub GUI.
- **FR-009**: The Porter Hub GUI (`frontend/index.html`, `frontend/admin_index.html`, `frontend/js/user_hub.js`, and `frontend/js/admin_hub.js`) MUST render an interactive **Jira ↔ Google Jules Command Center** widget and a **One-Shot Weekly Planning** widget wired to `/api/integrations/jira/status`, `/api/integrations/jira/sync`, `/api/integrations/jira/speckit-push`, `/api/integrations/jules/dispatch`, `/api/planning`, and `/api/user/hub_metrics` with full ARIA/label accessibility (`Palette` / `Fiona Protocol`).

### Key Entities

- **Unclassified Event Item (`EventToBeClassified`)**: Represents a raw calendar event staged in `events_to_be_classified` awaiting Hero or agent triage, scoped by `user_email` and deterministic UUIDv5.
- **Hub Progress Metrics Report (`HubProgressMetrics`)**: Represents the aggregated dashboard telemetry for an authenticated Hero, including intention counts, classified/unclassified event counts, matched intentions, valuable detours, and week-over-week detrimental detour delta.
- **Weekly Planning Payload (`WeeklyPlanningBatch`)**: Represents a Hero's one-shot weekly intention submission and the resulting structured list of planned intention blocks.
- **Artifact Gap Summary (`ArtifactGapReport`)**: Represents the list of empty or incomplete keys discovered across a Hero's `hero_origin.json` and `hero_ambition.json` artifacts, paired with a suggested Socratic discovery prompt.
- **Historical Journal Entry (`HistoricalJournalRecord`)**: Represents a persisted journal submission, its linked Socratic reflection, timestamp metadata, and pipeline `saga_status`.
- **Bridge Dashboard Status (`JiraJulesBridgeStatus`)**: Represents the combined GUI state for the Spec-Kit / Jira ↔ Google Jules Command Center, including active feature tasks, synced/staged Jira issues, recent Jules work orders, and environment readiness flags.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Authenticated Heroes can log a full week of intentions in a single interaction via `/api/planning` and see updated Hub Progress Metrics in under 3 seconds.
- **SC-002**: `/api/user/hub_metrics` computes all 6 required metrics (*Intentions Logged*, *Calendar Events Logged*, *Events to be Classified*, *Matched Intentions*, *Valuable Detours*, and *week-over-week Detrimental Detour improvements*) with 100% accuracy and zero cross-tenant data leakage.
- **SC-003**: 100% of empty fields in `hero_origin.json` and `hero_ambition.json` are accurately identified by the missing-artifact query service without failing when artifact files are missing or partially populated.
- **SC-004**: 100% of historical journal records returned to the review UI include a valid `saga_status` value (`RECEIVED`, `LLM_PROCESSING`, `GRAPH_INJECTED`, or `FAILED`).
- **SC-005**: All unit and contract tests for the feature execute completely offline using `mongomock` in under 2 seconds at $0.00 cloud cost.
- **SC-006**: Authenticated users can visually inspect Spec-Kit tasks, sync/push Jira tickets, preview formatted Jules Work Orders, and dispatch to Google Jules directly from the Porter Hub GUI (`index.html` and `admin_index.html`) in $\le 3$ clicks (20-Second Recon Loop compliance).

## Assumptions

- Authentication continues to rely on the existing JWT middleware (`@require_auth`) which populates `request.user_email` for all tenant-scoped endpoints.
- Existing collections (`event_intentions`, `event_actuals`, `unified_events`, `journals`) and `MongoConfig` constants in `src/config.py` serve as the baseline storage schema, extended with `EVENTS_TO_BE_CLASSIFIED_COLLECTION = "events_to_be_classified"`.
- Week-over-week Detrimental Detour improvement compares the count (or duration) of events classified as Detrimental Detours in the current 7-day window against the prior 7-day window.
