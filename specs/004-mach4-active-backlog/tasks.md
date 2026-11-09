---
description: "Task list for Mach 4 Active Swarm & Infrastructure Backlog (004-mach4-active-backlog)"
---

# Tasks: Mach 4 Active Swarm & Infrastructure Backlog

**Input**: Active domain requirements from `documentation/current-work/active-backend-tasks.md`, `documentation/current-work/active-agent-dev.md`, and `documentation/current-work/active-frontend-dev.md`  
**Prerequisites**: `002-jira-jules-bridge` and `003-first-serving-hub-api` completed and verified.  
**Tests**: Every task enforces Red-Green-Verify TDD (`make test-<persona>` + `make verify-done`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (isolated target files, safe for concurrent Google Jules dispatch)
- **[Story]**: User Story group (`US1` Resilience & Hub Runtime, `US2` Twin-Track & Observability, `US3` Frontend UX & Daily Recon)

---

## Phase 1: Completed Foundation & Verification Milestones (Done)

- [X] T101 [P] [US1] Implement `002-jira-jules-bridge` bi-directional `JiraClient`, `JiraStorage` batched `bulk_write`, and `JulesDispatcher` work orders in `src/integrations/jira_client.py` and `src/integrations/jules_dispatcher.py`
- [X] T102 [P] [US1] Implement `003-first-serving-hub-api` endpoints (`/api/user/hub_metrics`, `/api/planning`, `/api/calendar/classification_queue`, `/api/integrations/jira/status`) in `src/routes/jira_routes.py` and `src/routes/user_routes.py`
- [X] T103 [P] [US1] Modularize `scripts/porter_cli_agents.py` into `< 200`-line subcommand modules under `scripts/cli_agents/` (`env_git.py`, `prompt_builder.py`, `sync_verify.py`, `jules_sessions.py`, `jules_dispatch.py`)
- [X] T104 [P] [US1] Unify `SovereignMongoStorage` singleton client with fast `2500ms` local timeout and automatic `mongomock` dev fallback in `src/database/mongo_client/connection.py` and `src/database/mongo_storage.py`
- [X] T105 [P] [US1] Isolate `.jules/activity.log` telemetry during unit tests and lower `requires-python = ">=3.12"` in `pyproject.toml` and `tests/unit/test_jira_jules_bridge.py`

---

## Phase 2: Active Swarm Backlog — Database, Ingestion & Observability (To Do)

- [ ] T106 [P] [US2] Implement native MongoDB Time-Series collection schema and 1-month chronological batch queueing for historical calendar sync in `src/database/mongo_client/calendar_timeseries.py` and `src/database/mongo_storage.py`
- [ ] T107 [P] [US2] Update GTKY Historian and Librarian agents to output strict Pydantic v2 schemas for `formatted_calendar_events` in `src/agents/gtky_historian.py`, `src/agents/gtky_librarian.py`, and `src/schemas/api_models.py`
- [ ] T108 [P] [US2] Implement `first_serving_traces` and `first_serving_porter_happenings` observability collections and token request density circuit-breaker in `src/database/mongo_client/agent_health.py` and `src/agents/first_serving_porter.py`
- [ ] T109 [P] [US2] Wire multi-tenant `username` context threading across `src/routes/journal_routes.py`, `src/routes/chat_routes.py`, `src/routes/admin_routes.py`, and `src/agents/audit_inspector.py`
- [ ] T110 [P] [US2] Implement adversarial boundary & concurrency stress tests for `/api/process_journal` and `/api/get_calendar_events` in `tests/unit/test_blueprint_routes.py`

---

## Phase 3: Active Swarm Backlog — Frontend UX, A11y & DevOps Automation (To Do)

- [ ] T111 [P] [US3] Build rolling chronological `Adventure-calendar` component and lightweight API view in `frontend/js/user_hub.js` and `src/routes/calendar_routes.py`
- [ ] T112 [P] [US3] Refactor `/artifacts.html` (`Ambition & Intent`, `Hero Detriments`, `Pillars Mapping`) and `/graph_explorer` UX using semantic CSS variables and WCAG AA ARIA labels in `frontend/artifacts.html` and `frontend/graph_explorer.html`
- [ ] T113 [P] [US3] Add scheduled GitHub Action workflow for automated Google Jules session status polling and Jira ticket synchronization in `.github/workflows/main.yml` and `scripts/porter_cli_agents.py`
- [ ] T114 [P] [US3] Synchronize 3-Layer Rosetta Stone documentation (`AGENTS.md`, `.agents/agents/`, `.jules/`) and archive stale backups via `scripts/retention_engine.py` in `documentation/integrations.md`
