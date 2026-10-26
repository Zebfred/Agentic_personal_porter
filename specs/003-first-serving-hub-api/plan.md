# Implementation Plan: First-Serving Agent API, Porter Hub Support & Jira/Jules Bridge GUI

**Branch**: `003-first-serving-hub-api` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/003-first-serving-hub-api/spec.md`

## Summary

Deliver the complete backend API and interactive frontend Porter Hub GUI (`index.html`, `admin_index.html`, `journal_review.html`) for `003-first-serving-hub-api`:
1. **Hub Progress Metrics & Classification Queue (`US1`)**: Add `MongoConfig.EVENTS_TO_BE_CLASSIFIED_COLLECTION = "events_to_be_classified"`, batched staging/triage methods in `SovereignMongoStorage`, and `GET /api/user/hub_metrics` (`src/routes/user_routes.py`) computing all 6 Hero telemetry counters plus week-over-week Detrimental Detour improvement.
2. **First-Serving Chat, Dual-Artifact Gap Discovery & One-Shot Weekly Planning (`US2`)**: Extend `GTKYIdentityArchitect` (`src/agents/gtky_identity_architect.py`) to scan both `hero_origin.json` and `hero_ambition.json` with safe template fallbacks, and add `POST /api/planning` + `GET /api/planning` (`src/routes/journal_routes.py`) to parse and batch-persist a full week of intentions via `bulk_write(ops, ordered=False)`.
3. **Historical Journal Review with `saga_status` (`US3`)**: Ensure `save_freeform_journal`, `get_journal_and_expectation_history`, and `GET /api/journal/history` persist and return explicit `saga_status` (`RECEIVED`, `LLM_PROCESSING`, `GRAPH_INJECTED`, `FAILED`) and linked reflection text, rendered as status badges in `frontend/js/user_hub.js` and `frontend/js/journal_review.js`.
4. **Interactive Porter Hub GUI for Jira ↔ Google Jules Bridge (`US4`)**: Add `GET /api/integrations/jira/status` in `src/routes/jira_routes.py` and build the **Spec-Kit / Jira ↔ Google Jules Command Center** + **One-Shot Weekly Planning** UI panels in `frontend/index.html`, `frontend/admin_index.html`, `frontend/js/user_hub.js`, and `frontend/js/admin_hub.js` so all Jira and Jules workflows can be visually inspected and triggered in the browser in $\le 3$ clicks.

## Technical Context

**Language/Version**: Python 3.12+ / 3.14 (managed via `uv`), Vanilla ES6 JavaScript (`frontend/js/`), HTML5 + Tailwind CSS v4 (`frontend/css/input.css` -> `frontend/css/style.css`)  
**Primary Dependencies**: Flask, Pydantic v2, PyMongo (`mongomock` for unit tests), Neo4j Bolt driver, `requests`  
**Storage**: MongoDB (`events_to_be_classified`, `event_intentions`, `event_actuals`, `unified_events`, `weekly_expectations`, `journal_freeform_entries`, `hero_artifacts`, `jira_issues_staging`, `jules_work_orders`) & Neo4j Identity Graph  
**Testing**: `uv run pytest tests/unit -v --tb=short`, `make verify-done`, `make test-roster`  
**Target Platform**: Linux / Docker Compose / Local Workstation Browser GUI (`http://localhost:5001`)  
**Performance Goals**: `<50ms` local MongoDB queries via explicit field projections and compound indexes; `<2s` full unit test execution offline via `mongomock`; $\le 3$ clicks for any Hub GUI action (20-Second Recon Loop)  
**Constraints**: Zero hardcoded secrets (`.auth/.env` only), strict multi-tenant scoping via `request.user_email`, zero N+1 loops (mandatory `bulk_write`), explicit projections on all `.find()` calls, and zero workstation-specific absolute paths in docs or code.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Requirement | Status | Implementation Alignment |
| :--- | :--- | :--- | :--- |
| **I. Sovereign Privacy & Zero-Trust** | Secrets in `.auth/`, `@require_api_key` auth, sanitized errors, `shell=False` | **PASS** | All endpoints enforce `@require_api_key`; errors are sanitized; DOM updates escape HTML via `escapeHTML()`. |
| **II. Multi-Tenant Partitioning** | Dynamic `request.user_email`, composite UUIDv5 (`UUIDGenerator`), query scoping | **PASS** | All queries in `events_to_be_classified`, `hub_metrics`, `planning`, `artifacts`, and `jira/status` scope by `request.user_email`. |
| **III. Database Discipline** | Neo4j singleton driver, idempotent Cypher `MERGE`, MongoDB `bulk_write` + projections | **PASS** | `/api/planning` and classification queue staging use `bulk_write(ops, ordered=False)` and explicit projection dicts (`{"_id": 0, ...}`). |
| **IV. 20-Second Recon & A11y** | $\le 3$ clicks, semantic CSS tokens, `<label for>`, `aria-label`, async button states | **PASS** | New Hub GUI panels in `index.html` and `admin_index.html` include explicit `<label for>`, `aria-label`, and `finally` button state restoration. |
| **V. Non-Destructive Lifecycle** | `.bk` backups moved to `.legacy_hr/`, zero permanent deletion | **PASS** | All backups swept into `.legacy_hr/` and verified by `make test-docdoc`. |
| **VI. Documentation Supremacy** | Lowercase `documentation/` in `kebab-case.md`, relative paths only | **PASS** | Updated docs use relative paths and `kebab-case.md`, verified by `verify_doc_hygiene.py`. |
| **VII. Verification-Gated Delivery** | Contract-first Pydantic v2 schemas in `src/schemas/hub_models.py`, `make verify-done` | **PASS** | All request/response schemas defined in `src/schemas/hub_models.py` before route implementation. |
| **VIII. Preset Supremacy** | Local `.specify/memory/constitution.md` rules enforced | **PASS** | Checked against local Constitution v1.2.0. |
| **IX. Zero-Cost Local DB & TDD** | 100% offline unit tests via `mongomock` (`mock_mongo`) | **PASS** | `tests/unit/test_first_serving_hub_api.py` runs completely offline against `mongomock` and `mock_neo4j`. |

## Project Structure

### Documentation (this feature)

```text
specs/003-first-serving-hub-api/
├── spec.md              # Feature specification (US1-US4, FR-001..FR-009, SC-001..SC-006)
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 technical decisions
├── data-model.md        # Phase 1 Pydantic v2 schemas & MongoDB index contracts
├── quickstart.md        # Phase 1 CLI + Browser GUI verification guide
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── contracts/
    └── first-serving-hub-api-contract.json
```

### Source Code (repository root)

```text
src/
├── config.py                                  # Add EVENTS_TO_BE_CLASSIFIED_COLLECTION = "events_to_be_classified"
├── schemas/
│   └── hub_models.py                          # NEW: Pydantic v2 models for Hub metrics, classification queue, planning, artifacts, journal saga_status, and Jira/Jules GUI status
├── database/
│   └── mongo_storage.py                       # Add events_to_be_classified staging/query methods, calculate_hub_metrics(), batch save_weekly_intentions(), and saga_status in journal history
├── agents/
│   └── gtky_identity_architect.py             # Add scan_missing_artifacts() scanning both hero_origin.json and hero_ambition.json with default template fallback
└── routes/
    ├── user_routes.py                         # Add GET /user/hub_metrics (/api/user/hub_metrics)
    ├── calendar_routes.py                     # Wire GET/POST /api/calendar/classification_queue and delegate /api/calendar/adventure_log to calculate_hub_metrics()
    ├── journal_routes.py                      # Add POST/GET /api/planning (batched weekly planning) and include saga_status + reflection in GET /api/journal/history
    ├── inventory_routes.py                    # Return structured gaps + results in GET /api/artifacts/scan
    └── jira_routes.py                         # Add GET /api/integrations/jira/status for Porter Hub GUI Command Center

frontend/
├── index.html                                 # Add One-Shot Weekly Planning inputs & Spec-Kit / Jira <-> Google Jules Command Center section
├── admin_index.html                           # Add Spec-Kit / Jira <-> Google Jules Command Center section for Nexus-Guild Admins
└── js/
    ├── user_hub.js                            # Wire /api/user/hub_metrics, /api/planning, saga_status badges, and Jira/Jules Command Center GUI controls
    └── admin_hub.js                           # Wire Jira/Jules Command Center GUI controls on Admin Hub

tests/
└── unit/
    └── test_first_serving_hub_api.py          # NEW: Comprehensive offline unit & contract test suite for US1-US4
```

**Structure Decision**: Extends the existing modular Flask Blueprint + `SovereignMongoStorage` + Vanilla ES6 JS architecture without introducing new frameworks or circular dependencies (`src/config.py` <- `src/schemas/hub_models.py` <- `src/database/mongo_storage.py` <- `src/routes/*`).

## Complexity Tracking

No constitutional violations require justification. All 9 Core Principles pass cleanly.
