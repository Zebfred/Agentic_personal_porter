# Task Breakdown: North Star Accountability & Weekly Streak Engine (`004-north-star-accountability`)

**Feature Branch**: `feat/004-north-star-accountability` (Stacked on `feat/003-first-serving-hub-api`)

---

## Phase 1: Contract-First Schemas & Validation (Completed in Spec PR)

* [x] **T001** [`archie`] Create Pydantic v2 boundary contracts in `src/schemas/accountability_models.py` (`NorthStarPillar`, `PillarUpsertBatchRequest`, `ReconCheckInRequest`, `GraceWindowRequest`, `PillarStreakSummary`, `AccountabilityDashboardResponse`) with strict null-byte, slug, ISO-week, and bounds validation.
* [x] **T002** [`crii`] Add unit & adversarial boundary fuzzing tests in `tests/unit/test_accountability_models.py` verifying slug constraints, null-byte rejection, batch size cap (`<= 6`), and restorative pillar defaults.

## Phase 2: Storage & Deterministic Streak Engine (PR #2)

* [x] **T003** [`bolt`] Add collection constants (`NORTH_STAR_PILLARS_COLLECTION`, `PILLAR_CHECKINS_COLLECTION`, `GRACE_WINDOWS_COLLECTION`) in `src/config.py` and implement projected, indexed Mongo storage with `mongomock` fallback in `src/database/mongo_client/accountability_storage.py`.
* [x] **T004** [`backend-porter`] Implement deterministic ISO-week streak calculator, Grace/Vacation freeze logic, and `markdownlint`-compliant Markdown snapshot renderer in `src/services/accountability_service.py` (`< 200` lines, zero LLM calls).
* [x] **T005** [`bolt`] Add idempotent Neo4j `MERGE` helpers for `(:Hero)-[:PURSUES]->(:NorthStarPillar)` and `(:PillarCheckIn)` using the singleton connection pool.

## Phase 3: Flask Blueprint & Security Hardening (PR #2)

* [x] **T006** [`backend-porter`] Implement `src/routes/accountability_routes.py` Blueprint (`/api/accountability/*`) and register it in `src/app.py`.
* [x] **T007** [`sentinel`] Audit JWT `request.user_email` scoping, idempotency deduplication, and sanitized error responses across all 6 endpoints; add tenant-isolation unit tests in `tests/unit/test_accountability_service.py` and `tests/unit/test_accountability_routes.py`.

## Phase 4: Porter Hub 20-Second Recon UI (PR #3)

* [x] **T008** [`frontend-porter`, `palette`] Add North Star Pillar chips, one-tap check-in button with async loading state, Grace Mode toggle, and Life Harmony badge to `frontend/index.html`, `frontend/js/accountability_widget.js`, and `frontend/js/user_hub.js` using semantic CSS tokens and WCAG ARIA labels.
* [x] **T009** [`silas`] Run `make verify-done` (`ruff`, `mypy`, `bandit`, `pytest tests/unit`, `node -c`) and update `documentation/current-work/active-backend-tasks.md` and `documentation/current-work/active-frontend-dev.md`.
