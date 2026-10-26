---
description: "Task list for First-Serving Agent API, Porter Hub Support & Jira/Jules Bridge GUI (003-first-serving-hub-api)"
---

# Tasks: First-Serving Agent API, Porter Hub Support & Jira/Jules Bridge GUI

**Input**: Design documents from `/specs/003-first-serving-hub-api/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/first-serving-hub-api-contract.json`  
**Tests**: Included per Constitution Principle VII (Red-Green-Verify TDD) and Principle IX (`mongomock` offline unit testing).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`, `US4`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configure MongoDB collection constants for the Event Classification Queue.

- [X] T001 Add `EVENTS_TO_BE_CLASSIFIED_COLLECTION = "events_to_be_classified"` to `MongoConfig` in `src/config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Pydantic v2 boundary contracts and MongoDB index definitions required by all user stories.

- [X] T002 Create `src/schemas/hub_models.py` defining `SagaStatusType`, `EventToBeClassified`, `ClassificationQueueRequestSchema`, `HubProgressMetrics`, `WeeklyIntentionItem`, `WeeklyPlanningRequestSchema`, `ArtifactGapItem`, `ArtifactGapReport`, `HistoricalJournalRecord`, and `JiraJulesBridgeStatus`
- [X] T003 Register `events_to_be_classified` collection pointer and compound indexes `(user_email, status, start_time DESCENDING)` in `SovereignMongoStorage._ensure_indexes()` in `src/database/mongo_storage.py`

**Checkpoint**: Foundation ready — user story implementation can begin.

---

## Phase 3: User Story 1 - Hub Progress Metrics & Event Classification Queue (Priority: P1) 🎯 MVP

**Goal**: Provide real-time weekly Hub Progress Metrics (`/api/user/hub_metrics`) and a dedicated staging queue (`events_to_be_classified`) for unclassified calendar events.

**Independent Test**: Seed tenant-scoped intentions, actuals, and unclassified events across current and prior 7-day windows, query `/api/user/hub_metrics` and `/api/calendar/classification_queue`, and verify exact metric calculations and strict tenant isolation.

### Tests for User Story 1

- [X] T004 [P] [US1] Write offline unit and contract tests for `events_to_be_classified` staging, deduplication, and `GET /api/user/hub_metrics` in `tests/unit/test_first_serving_hub_api.py`

### Implementation for User Story 1

- [X] T005 [US1] Implement `stage_events_for_classification()`, `get_events_to_be_classified()`, and `calculate_hub_metrics()` using explicit projections and batched `bulk_write(ops, ordered=False)` in `src/database/mongo_storage.py`
- [X] T006 [US1] Implement `GET /user/hub_metrics` (`/api/user/hub_metrics`) in `src/routes/user_routes.py`
- [X] T007 [US1] Implement `GET /api/calendar/classification_queue` and `POST /api/calendar/classification_queue` and delegate `GET /api/calendar/adventure_log` to `calculate_hub_metrics()` in `src/routes/calendar_routes.py`

**Checkpoint**: User Story 1 is functional and independently testable.

---

## Phase 4: User Story 4 - Interactive Porter Hub GUI for Jira ↔ Google Jules Bridge (Priority: P1)

**Goal**: Surface the Spec-Kit / Jira ↔ Google Jules Bridge and One-Shot Weekly Planning directly in the Porter Hub browser GUI (`frontend/index.html` and `frontend/admin_index.html`) so all tasks, Jira tickets, and Jules Work Orders can be inspected, previewed, and dispatched visually in $\le 3$ clicks.

**Independent Test**: Call `GET /api/integrations/jira/status` and load `frontend/index.html` / `frontend/admin_index.html` to verify Spec-Kit tasks, Jira sync buttons, Work Order preview drawer, and Jules dispatch controls.

### Tests for User Story 4

- [X] T008 [P] [US4] Write offline unit and contract tests for `GET /api/integrations/jira/status` in `tests/unit/test_first_serving_hub_api.py`

### Implementation for User Story 4

- [X] T009 [US4] Implement `GET /integrations/jira/status` (`/api/integrations/jira/status`) in `src/routes/jira_routes.py` returning active Spec-Kit feature tasks, staged Jira issues, recent Jules work orders, and readiness flags
- [X] T010 [P] [US4] Add accessible (`<label for>`, `aria-label`, semantic tokens) **Spec-Kit / Jira ↔ Google Jules Command Center** and **One-Shot Weekly Planning** sections to `frontend/index.html` and `frontend/admin_index.html`
- [X] T011 [US4] Wire `/api/user/hub_metrics`, `/api/planning`, `/api/integrations/jira/status`, `/api/integrations/jira/sync`, `/api/integrations/jira/speckit-push`, and `/api/integrations/jules/dispatch` in `frontend/js/user_hub.js` and `frontend/js/admin_hub.js`

**Checkpoint**: User Story 4 GUI and backend status endpoint are functional and verifiable in the browser.

---

## Phase 5: User Story 2 - First-Serving Chat, Missing Artifact Discovery & One-Shot Weekly Planning (Priority: P2)

**Goal**: Enable missing-artifact discovery across both `hero_origin.json` and `hero_ambition.json` (with safe template fallbacks) and one-shot weekly intention batch persistence via `/api/planning`.

**Independent Test**: Invoke `GET /api/artifacts/scan` for a tenant with uninitialized or partially populated origin/ambition artifacts and `POST /api/planning` with a weekly intention plan, verifying gap detection and batched `event_intentions` persistence.

### Tests for User Story 2

- [X] T012 [P] [US2] Write offline unit and contract tests for dual-artifact gap scanning (`hero_origin.json` & `hero_ambition.json`) and `POST /api/planning` in `tests/unit/test_first_serving_hub_api.py`

### Implementation for User Story 2

- [X] T013 [US2] Implement `scan_missing_artifacts()` in `src/agents/gtky_identity_architect.py` and update `GET /api/artifacts/scan` in `src/routes/inventory_routes.py` to scan both `hero_origin.json` and `hero_ambition.json`
- [X] T014 [US2] Implement `save_weekly_intentions_batch()` in `src/database/mongo_storage.py` and `POST /api/planning` + `GET /api/planning` in `src/routes/journal_routes.py`

**Checkpoint**: User Story 2 is functional and independently testable.

---

## Phase 6: User Story 3 - Historical Journal Review & Saga Status Tracking (Priority: P3)

**Goal**: Return reverse-chronological journal and expectation records with explicit `saga_status` (`RECEIVED`, `LLM_PROCESSING`, `GRAPH_INJECTED`, `FAILED`) and linked reflection text for the Hub and `journal_review.html`.

**Independent Test**: Persist freeform and weekly journal entries across multiple dates and verify `GET /api/journal/history` returns reverse-chronological records with valid `saga_status` values.

### Tests for User Story 3

- [X] T015 [P] [US3] Write offline unit and contract tests for `saga_status` persistence and `GET /api/journal/history` in `tests/unit/test_first_serving_hub_api.py`

### Implementation for User Story 3

- [X] T016 [US3] Update `save_freeform_journal()` and `get_journal_and_expectation_history()` in `src/database/mongo_storage.py`, `GET /api/journal/history` in `src/routes/journal_routes.py`, and `frontend/js/journal_review.js` to persist, return, and render explicit `saga_status` badges

**Checkpoint**: All user stories (`US1`–`US4`) are functional and independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Compile frontend CSS, update active domain documentation, clean backups into `.legacy_hr/`, and run all persona verification gates.

- [X] T017 [P] Compile Tailwind CSS (`make build-css`), update `documentation/current-work/active-backend-tasks.md` and `documentation/current-work/active-frontend-dev.md`, and move all `.bk` backup files into `.legacy_hr/`
- [X] T018 Execute `make verify-done` and `make test-roster` to verify 0 lint/type errors, 100% passing unit tests, and 100% passing persona checks

---

## Dependencies & Execution Order

- **Phase 1 (`T001`)** → **Phase 2 (`T002`–`T003`)** → **Phases 3–6 (`US1`, `US4`, `US2`, `US3`)** → **Phase 7 (`T017`–`T018`)**
- Within each User Story phase, contract tests (`T004`, `T008`, `T012`, `T015`) are authored alongside storage/route implementations and verified offline via `mongomock`.
