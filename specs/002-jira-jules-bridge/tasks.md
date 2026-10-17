# Tasks: Unified Spec-Kit, Jira, and Jules Bridge

**Input**: Design documents from `/specs/002-jira-jules-bridge/`
**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (required for user stories), [research.md](research.md), [data-model.md](data-model.md), [contracts/jira-jules-bridge-contract.json](contracts/jira-jules-bridge-contract.json), [quickstart.md](quickstart.md)

**Tests**: Included in accordance with **Constitution Principle VII (3-Step Red-Green-Verify TDD Loop)** and **Principle IX (Zero-Cost Local DB & `mongomock` TDD)**.

**Organization**: Tasks are grouped by user story (`US1`, `US2`, `US3`) to enable independent implementation and testing of each story increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Exact file paths and verbatim `data-model.md` validation constraints are included in task descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configure MongoDB collection constants, deterministic UUID namespace, and Spec-Kit extension hook metadata.

- [X] T001 Add `JIRA_STAGING_COLLECTION = "jira_issues_staging"` and `JULES_WORK_ORDERS_COLLECTION = "jules_work_orders"` constants to `MongoConfig` in `src/config.py`
- [X] T002 [P] Extend `UUIDGenerator` with `NAMESPACE_JIRA` and `generate_for_jira_issue(cls, jira_key: str, user_email: str) -> str` deterministic UUIDv5 helper in `src/database/mongo_client/uuid_manager.py`
- [X] T003 [P] Create Spec-Kit extension hook configuration registering `hooks.after_tasks` and `hooks.before_taskstoissues` for `speckit_jira_bridge` in `.specify/extensions.yml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Pydantic v2 schemas and batched MongoDB storage layer that MUST be complete before user stories can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Define `PersonaType` (`"sentinel"`, `"bolt"`, `"palette"`, `"archie"`, `"docdoc"`, `"dave"`, `"crii"`, `"jovol"`, `"silas"`) and `SyncStatus` (`"synced"`, `"pending_upstream"`, `"unlinked"`, `"conflict"`) literals and base schemas in `src/schemas/jira_models.py`
- [X] T005 Define `SpecKitTaskItem` (`task_id` regex `^T\d{3,}$`, `feature_id` `min_length=3, max_length=120`, `title` `min_length=3, max_length=255`, `description` `max_length=15000`, `is_parallel` default `False`, `user_story` regex `^US\d+$` or `None`, `target_paths` default `[]`, `persona` default `"silas"`, `completed` default `False`), `JiraIssueRecord` (`uuid` Deterministic UUIDv5, `user_email` required non-empty, `jira_key` regex `^([A-Z][A-Z0-9_]+-\d+|LOCAL-T\d{3,})$`, `project_key` regex `^[A-Z][A-Z0-9_]+$`, `issue_type` `Literal["Epic", "Story", "Task", "Sub-task"]` default `"Task"`, `task_id` regex `^T\d{3,}$` or `None`, `feature_id` `max_length=120`, `epic_key` `max_length=64`, `summary` `min_length=1, max_length=255`, `description` `max_length=20000`, `status` default `"To Do"`, `persona` default `"silas"`, `labels` default `[]`, `sync_status` default `"synced"`, `correlation_id` non-empty string, `jules_session_id` `max_length=128`, `updated_at` ISO-8601 UTC timestamp), and `JulesWorkOrder` (`work_order_id` Deterministic UUIDv5, `user_email` required non-empty, `jira_key` required, `task_id` regex `^T\d{3,}$` or `None`, `feature_id` required, `persona` required, `playbook_path` relative path, `target_paths` default `[]`, `verification_commands` non-empty, `formatted_prompt` `min_length=20, max_length=30000`, `dry_run` default `True`, `dispatch_status` `Literal["preview", "queued", "dispatched", "failed"]` default `"preview"`, `jules_session_id` `None` or session string, `correlation_id` non-empty string) models in `src/schemas/jira_models.py`
- [X] T006 Implement `JiraStorage` with compound indexes (`[("user_email", ASCENDING), ("updated_at", DESCENDING)]`, `[("user_email", ASCENDING), ("jira_key", ASCENDING)]`), explicit query projections (`{"_id": 0, "jira_key": 1, "task_id": 1, "status": 1, "sync_status": 1}`), and batched `bulk_write(ops, ordered=False)` persistence in `src/database/mongo_client/jira_storage.py`

**Checkpoint**: Foundation ready — user story implementation can now proceed.

---

## Phase 3: User Story 1 - Bi-Directional Jira Issue Synchronization (Read & Write Foundation) (Priority: P1) 🎯 MVP

**Goal**: Enable authenticated tenants to pull active Jira sprint/project issues into local MongoDB/Neo4j storage and push new issues, status transitions, and comments upstream with offline `pending_upstream` resilience.

**Independent Test**: Run `uv run pytest tests/unit/test_jira_jules_bridge.py -k "us1 or jira_client"` offline with `mongomock` and mocked HTTP responses to verify pull, push, transition, rate-limit fallback, and Neo4j `Quest:Intention` Cypher merging.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST and verify they fail before implementing `src/integrations/jira_client.py`**

- [X] T007 [P] [US1] Author offline unit and contract tests for `JiraClient` credential validation, URL sanitization, pull, create, transition, comment, and offline `pending_upstream` queuing in `tests/unit/test_jira_jules_bridge.py`

### Implementation for User Story 1

- [X] T008 [US1] Implement `JiraClient` with `.auth/.env` zero-trust credential loading (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`), `urllib.parse.urlparse` host validation, and `invoke_with_retry` REST v3 methods (`fetch_issues`, `create_issue`, `transition_issue`, `add_comment`) in `src/integrations/jira_client.py`
- [X] T009 [US1] Add idempotent Neo4j `(:Hero)-[:PURSUES_QUEST]->(:Quest:Intention)` merge helper and bi-directional sync (`sync_tenant_jira_issues` with `pending_upstream` flush) in `src/database/mongo_client/jira_storage.py`
- [X] T010 [US1] Implement `POST /api/integrations/jira/sync` route in `src/routes/jira_routes.py` and register `jira_bp` blueprint in `src/app.py`

**Checkpoint**: User Story 1 is complete and independently testable via `tests/unit/test_jira_jules_bridge.py`.

---

## Phase 4: User Story 2 - Spec-Kit to Jira Standardized Issue Creation Hook (Priority: P2)

**Goal**: Provide a standardized Spec-Kit parser and synchronization hook that converts `spec.md`, `plan.md`, and `tasks.md` into deduplicated Jira Epics and child Stories/Tasks (`T001`+) enriched with `.jules/<persona>.md` assignments.

**Independent Test**: Run `uv run pytest tests/unit/test_jira_jules_bridge.py -k "us2 or speckit"` and `uv run python -m src.orchestrators.speckit_jira_bridge --feature-dir specs/002-jira-jules-bridge --dry-run` to verify `tasks.md` parsing, persona inference, and `T001`+ deduplication.

### Tests for User Story 2 ⚠️

- [X] T011 [P] [US2] Author unit tests for `tasks.md` regex parsing (`\bT\d{3,}\b`), persona domain mapping, and idempotent `T001`+ deduplication across open/closed issues in `tests/unit/test_jira_jules_bridge.py`

### Implementation for User Story 2

- [X] T012 [US2] Implement `parse_speckit_feature`, persona inference mapper, and idempotent Epic + child Story/Task synchronization (`sync_feature_to_jira`) with `--dry-run` and `--push` CLI support in `src/orchestrators/speckit_jira_bridge.py`
- [X] T013 [US2] Implement `POST /api/integrations/jira/speckit-push` endpoint in `src/routes/jira_routes.py`

**Checkpoint**: User Stories 1 and 2 work both independently and together.

---

## Phase 5: User Story 3 - Automated Formatting and Dispatch of Jira Tickets to Jules (Priority: P3)

**Goal**: Format standardized Jira tickets and Spec-Kit tasks into self-contained `JulesWorkOrder` packages (injecting `.jules/<persona>.md` rules and `make test-<persona>` + `make verify-done` gates) and dispatch them via `@google/jules` while annotating the Jira ticket with session lineage.

**Independent Test**: Run `uv run pytest tests/unit/test_jira_jules_bridge.py -k "us3 or jules"` and `uv run python -m src.orchestrators.speckit_jira_bridge --feature-dir specs/002-jira-jules-bridge --dispatch-task T001 --dry-run` to verify prompt assembly, playbook injection, pre-dispatch validation, and Jira session annotation.

### Tests for User Story 3 ⚠️

- [X] T014 [P] [US3] Author unit tests for `JulesDispatcher` work order assembly, `.jules/<persona>.md` playbook injection, pre-dispatch validation errors, `subprocess.run(..., shell=False)` safety, and Jira session comment annotation in `tests/unit/test_jira_jules_bridge.py`

### Implementation for User Story 3

- [X] T015 [US3] Implement `JulesDispatcher` (`build_work_order`, `dispatch_work_order` with `shell=False` and `dry_run` support) in `src/integrations/jules_dispatcher.py`
- [X] T016 [US3] Wire `--dispatch-task` and `--execute-jules` CLI flags into `src/orchestrators/speckit_jira_bridge.py` and implement `POST /api/integrations/jules/dispatch` in `src/routes/jira_routes.py`

**Checkpoint**: All 3 user stories (`US1`, `US2`, `US3`) are independently functional and verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Expose convenient `Makefile` targets, update project documentation and active sprint trackers, clean up `.bk` backups, and pass all automated quality gates.

- [X] T017 [P] Add `sync-jira` and `jules-dispatch` targets to `Makefile`
- [X] T018 [P] Document the Unified Spec-Kit / Jira ↔ Jules Bridge in `documentation/integrations.md` and record task completion in `documentation/current-work/active-backend-tasks.md`
- [X] T019 Archive any `.bk` backup files into `.legacy_hr/` and execute `make verify-done` and `make test-roster` across the repository

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1: `T001`–`T003`)**: No dependencies — can start immediately.
- **Foundational (Phase 2: `T004`–`T006`)**: Depends on Phase 1 completion — BLOCKS all user stories.
- **User Story 1 (Phase 3: `T007`–`T010`)**: Depends on Phase 2 completion. Delivers MVP bi-directional Jira sync.
- **User Story 2 (Phase 4: `T011`–`T013`)**: Depends on Phase 2 and `JiraClient` (`T008`). Delivers Spec-Kit `tasks.md` → Jira Epic/Task creation and deduplication.
- **User Story 3 (Phase 5: `T014`–`T016`)**: Depends on Phase 2 and integrates with `US1`/`US2` models to format and dispatch `JulesWorkOrder` packages.
- **Polish (Phase 6: `T017`–`T019`)**: Depends on completion of Phases 3–5.

### Parallel Opportunities

- **Phase 1**: `T002` (`src/database/mongo_client/uuid_manager.py`) and `T003` (`.specify/extensions.yml`) can run in parallel with `T001` (`src/config.py`).
- **Contract/Unit Tests**: `T007` (`[US1]`), `T011` (`[US2]`), and `T014` (`[US3]`) test suites can be authored prior to their respective service implementations.
- **Phase 6**: `T017` (`Makefile`) and `T018` (`documentation/integrations.md`) touch independent files and can run in parallel before final gate verification (`T019`).

---

## Parallel Example: User Story 1, 2 & 3 Modules

```bash
# Phase 1 parallel execution:
Task T001: "Add JIRA_STAGING_COLLECTION and JULES_WORK_ORDERS_COLLECTION to src/config.py"
Task T002: "Extend UUIDGenerator with generate_for_jira_issue in src/database/mongo_client/uuid_manager.py"
Task T003: "Create Spec-Kit extension hook configuration in .specify/extensions.yml"

# Service-level parallel execution after Phase 2 (T004-T006) completes:
Task T008: "Implement JiraClient in src/integrations/jira_client.py"
Task T015: "Implement JulesDispatcher in src/integrations/jules_dispatcher.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001`–`T003`)
2. Complete Phase 2: Foundational (`T004`–`T006`)
3. Complete Phase 3: User Story 1 (`T007`–`T010`)
4. **STOP and VALIDATE**: Run `uv run pytest tests/unit/test_jira_jules_bridge.py -k "us1"`

### Incremental Delivery

1. **Foundation (`T001`–`T006`)** → Pydantic v2 contracts & batched MongoDB storage ready.
2. **MVP (`T007`–`T010`)** → Bi-directional Jira read/write client + `/api/integrations/jira/sync`.
3. **Spec-Kit Hook (`T011`–`T013`)** → `tasks.md` → Jira Epic/Tasks with `T001`+ deduplication.
4. **Jules Bridge (`T014`–`T016`)** → `.jules/<persona>.md` work order formatter & `@google/jules` dispatcher.
5. **Polish & Gate (`T017`–`T019`)** → `Makefile`, docs, `.legacy_hr` cleanup, `make verify-done`, and `make test-roster`.
