# Implementation Plan: Unified Spec-Kit, Jira, and Jules Bridge

**Branch**: `002-jira-jules-bridge` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-jira-jules-bridge/spec.md`

## Summary

Build a sovereign, bi-directional **Spec-Kit ↔ Atlassian Jira ↔ Google Jules Bridge** for the Agentic Personal Porter. First, implement a zero-trust, resilient **Atlassian Jira Read/Write Client** (`src/integrations/jira_client.py`) backed by tenant-partitioned MongoDB staging (`src/database/mongo_client/jira_storage.py`) and Neo4j Quest/Intention graph syncing. Second, wire a **Spec-Kit Standardization Hook & Orchestrator** (`src/orchestrators/speckit_jira_bridge.py` + `.specify/extensions.yml`) that parses `spec.md`, `plan.md`, and `tasks.md` into deduplicated Jira Epics and child Tasks (`T001`+) enriched with `.jules/<persona>.md` assignments. Third, build the **Jules Work Order Formatter & Dispatcher** (`src/integrations/jules_dispatcher.py` + Flask routes in `src/routes/jira_routes.py`) to bundle Jira tickets, Spec-Kit acceptance criteria, persona prevention rules, and mandatory `make test-<persona>` / `make verify-done` verification gates into asynchronous `@google/jules` coding sessions.

## Technical Context

**Language/Version**: Python 3.12+ (up to 3.14) managed via `uv` in Conda environment `agentic_porter`

**Primary Dependencies**: Flask, Pydantic v2 (`src/schemas/`), `requests` + `tenacity` (`src/utils/retry_utils.py`), PyMongo / `mongomock`, Neo4j Python Driver, `@google/jules` CLI

**Storage**:
- MongoDB (`jira_issues_staging` and `jules_work_orders` collections via `mongo:7.0` locally and `mongomock` in unit tests)
- Neo4j Identity Graph (`(:Hero)-[:PURSUES_QUEST]->(:Quest:Intention)`)
- Local Filesystem (`.auth/.env` zero-trust secrets, `.specify/extensions.yml` hook config, `.jules/*.md` persona playbooks)

**Testing**: `pytest` (`tests/unit/test_jira_jules_bridge.py` with `mongomock`), `ruff check`, `mypy`, `make test-roster`, and `make verify-done`

**Target Platform**: Cross-platform Linux / Windows development environment and Dockerized Gunicorn WSGI production runtime

**Project Type**: Modular Flask web service + Spec-Kit CLI/hook automation + Agentic orchestrator

**Performance Goals**:
- Spec-Kit 25-task batch formatting and Jira deduplication check in `< 15s` live / `< 50ms` mocked
- Zero $O(n)$ sequential MongoDB writes (100% batched via `bulk_write(ops, ordered=False)`)
- Full offline unit test suite execution in `< 2.0s` at `$0.00` cloud cost

**Constraints**:
- Zero-trust credential storage in `.auth/.env` (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`); fail-fast validation on missing configuration
- Domain-safe URL validation via `urllib.parse.urlparse` and `shell=False` subprocess execution (`sentinel` compliance)
- Explicit MongoDB projection dictionaries on all batch queries (`bolt` compliance)
- Multi-tenant scoping by `user_email` and deterministic UUIDv5 generation (`UUIDGenerator.generate_for_jira_issue`)
- Non-destructive `.bk` backup creation and `.legacy_hr/` cleanup (`docdoc` compliance)

**Scale/Scope**: Supports multi-tenant users syncing hundreds of sprint issues and Spec-Kit features (`T001`–`T9999+`) across all 8 specialized quality personas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Invariant Under Evaluation | Pre-Design | Post-Design | Validation Notes |
| :--- | :--- | :---: | :---: | :--- |
| **I. Sovereign Privacy & Zero-Trust** | Secrets in `.auth/.env` only; fail-secure validation; `hmac.compare_digest` on auth middleware; no stack trace exposure. | **PASS** | **PASS** | `JiraClient` loads credentials strictly from environment (`.auth/.env`), validates base URL hostname via `urllib.parse.urlparse`, and sanitizes HTTP errors. |
| **II. Multi-Tenant Partitioning** | Dynamic `request.user_email`; no `HERO_NAME`; composite deterministic UUIDs. | **PASS** | **PASS** | Added `UUIDGenerator.generate_for_jira_issue(jira_key, user_email)`; all Mongo and Neo4j queries scope by `user_email`. |
| **III. Database Discipline** | Neo4j singleton pooling; idempotent Cypher `MERGE`; MongoDB batched `bulk_write(ops, ordered=False)`. | **PASS** | **PASS** | `jira_storage.py` uses `bulk_write` with explicit projections `{"_id": 0, ...}` and `DESCENDING` temporal indexes. |
| **IV. 20-Second Recon & A11y** | Fast action workflows; semantic tokens; WCAG compliance. | **PASS** | **PASS** | Backend API and CLI hooks require zero extra UI clicks during daily recon; optional UI triggers stay within $\le 3$ clicks. |
| **V. Non-Destructive Lifecycle** | Outdated files moved to `.legacy_hr/`; `.bk` backups created before edits and archived upon completion. | **PASS** | **PASS** | Enforced across all Spec-Kit artifacts and existing source file modifications. |
| **VI. Documentation Supremacy** | Markdown docs in `documentation/` with `kebab-case.md`; Spec-Kit artifacts in `specs/002-jira-jules-bridge/`. | **PASS** | **PASS** | Verified via `make test-docdoc` (`verify_doc_hygiene.py`). |
| **VII. Verification-Gated Delivery**| Contract-first Pydantic v2 schemas (`src/schemas/jira_models.py`); Red-Green-Verify TDD; `make verify-done`. | **PASS** | **PASS** | Complete Pydantic v2 models and contract JSON defined in Phase 1 prior to implementation. |
| **VIII. Preset Supremacy** | Local `.specify/memory/constitution.md` supersedes external templates. | **PASS** | **PASS** | Local `.specify/extensions.yml` hook respects project constitution invariants. |
| **IX. Zero-Cost Local DB & TDD** | Unit tests use `mongomock` offline with `< 10ms` per test and `$0.00` cloud cost. | **PASS** | **PASS** | `tests/unit/test_jira_jules_bridge.py` runs 100% offline with `mock_mongo` and mocked REST/CLI calls. |

*GATE RESULT: ALL 9 CONSTITUTIONAL PRINCIPLES PASSED PRE- AND POST-DESIGN.*

## Project Structure

### Documentation (this feature)

```text
specs/002-jira-jules-bridge/
├── spec.md                                  # Feature specification
├── plan.md                                  # This implementation plan
├── research.md                              # Phase 0 architecture & integration decisions
├── data-model.md                            # Phase 1 Pydantic v2 models & DB schemas
├── quickstart.md                            # Phase 1 runnable CLI & test validation guide
├── contracts/
│   └── jira-jules-bridge-contract.json      # Phase 1 endpoint, CLI & hook schema contract
├── checklists/
│   └── requirements.md                      # Specification quality checklist (16/16 passed)
└── tasks.md                                 # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
.specify/
└── extensions.yml                           # Spec-Kit hook registration (before_taskstoissues / after_tasks)

src/
├── config.py                                # Add JIRA_STAGING_COLLECTION & JULES_WORK_ORDERS_COLLECTION to MongoConfig
├── app.py                                   # Register jira_bp blueprint (/api/integrations)
├── schemas/
│   └── jira_models.py                       # Pydantic v2 models: SpecKitTaskItem, JiraIssueRecord, JulesWorkOrder, Sync requests
├── database/
│   └── mongo_client/
│       ├── uuid_manager.py                  # Add UUIDGenerator.generate_for_jira_issue(jira_key, user_email)
│       └── jira_storage.py                  # Batched bulk_write, projected queries, pending_upstream queue & indexes
├── integrations/
│   ├── jira_client.py                       # Zero-trust Atlassian Jira REST v3 read/write client with tenacity retry
│   └── jules_dispatcher.py                  # Formats Jira + Spec-Kit + .jules/<persona>.md into JulesWorkOrder & invokes @google/jules
├── orchestrators/
│   └── speckit_jira_bridge.py               # Parses spec.md/plan.md/tasks.md, deduplicates T001+, syncs Jira & dispatches to Jules
└── routes/
    └── jira_routes.py                       # Flask Blueprint: /api/integrations/jira/sync, /speckit-push, /jules/dispatch

tests/
└── unit/
    └── test_jira_jules_bridge.py            # Offline unit & contract tests (mongomock, retry resilience, deduplication, Jules formatting)
```

**Structure Decision**: Extends the existing modular Flask and orchestrator layout (`src/schemas/`, `src/database/mongo_client/`, `src/integrations/`, `src/orchestrators/`, `src/routes/`, and `tests/unit/`), keeping strict unidirectional layering (`schemas` -> `database`/`integrations` -> `orchestrators` -> `routes`) as required by **Archie** (`.jules/archie.md`).

## Complexity Tracking

> *Constitution Check has zero violations. Key architectural trade-offs are recorded below for traceability.*

| Design Area | Chosen Approach | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Jira HTTP Layer** | Custom `JiraClient` using `requests` + `invoke_with_retry` + Pydantic v2 schemas | Third-party SDKs add untyped bloat and hide HTTP 429 headers needed for offline `pending_upstream` fallback. |
| **Spec-Kit Hook Integration** | Native Python orchestrator registered in `.specify/extensions.yml` | Community extensions (`discovery-only`) cannot write to Porter's multi-tenant MongoDB/Neo4j or inject `.jules/*.md` playbooks. |
| **Jules Invocation** | `subprocess.run(["jules", "new", ...], shell=False)` with `--dry-run` default | Direct shell strings risk command injection; defaulting to `dry_run=True` prevents accidental remote VM spin-up during previews. |
