# Feature Specification: North Star Accountability & Weekly Streak Engine

**Feature Branch**: `feat/004-north-star-accountability`

**Created**: 2026-11-22

**Status**: Draft (Stacked on `feat/003-first-serving-hub-api`)

**Input**: Extend the Agentic Personal Porter's existing 20-Second Recon Loop, Hub Progress Metrics (`003-first-serving-hub-api`), and Neo4j Identity Graph with a low-friction, non-judgmental Accountability Progress Tracker covering Career Fundamentals, Business/FinOps, Builder/Joy Fuel, and Protected Life & Relationship Time, plus a one-command Markdown snapshot export for Git/mobile access.

---

## 1. User Scenarios & Testing *(mandatory)*

### User Story 1 - North Star Pillars Configuration & Weekly Streak Tracking (Priority: P1)

As an authenticated Hero balancing high-ambition career/business goals with family and relationship priorities, I want to define up to 6 **North Star Pillars** (such as *Career Fundamentals*, *Nexus Business & FinOps*, *Builder / Joy Fuel*, and *Protected Life & Relationship Time*) with realistic weekly micro-targets, so that the Porter tracks my small consistent wins without guilt or burnout.

**Why this priority**: Solves the core "goals drop off completely when life gets busy" failure mode by replacing sprawling to-do lists with 4–6 small, sustainable weekly streaks tied directly to existing Porter telemetry.

**Independent Test**: Seed a tenant with 4 pillars (including `is_restorative_life_pillar=True`), log qualifying check-ins across 2 consecutive ISO weeks, query `GET /api/accountability/streaks`, and verify exact streak counts, weekly completion ratios, and strict `user_email` tenant isolation.

**Acceptance Scenarios**:

1. **Given** an authenticated Hero with 4 configured North Star Pillars, **When** the Hero logs a qualifying 20-Second Recon check-in tagged to a pillar, **Then** the pillar's weekly progress increments and the active streak updates deterministically with zero LLM calls required.
2. **Given** a Hero logs protected non-work time (date night, family visit, restorative rest) under a life/relationship pillar, **When** weekly accountability metrics are computed, **Then** the system counts it as a **first-class win** toward overall life-alignment score rather than an idle gap.
3. **Given** two different authenticated Heroes, **When** either Hero queries pillars, check-ins, or streaks, **Then** zero records from the other Hero are ever exposed.

---

### User Story 2 - 20-Second Recon Loop Pillar Check-In & Zero-Guilt Grace Windows (Priority: P1)

As a busy Hero on vacation or facing a heavy life week, I want to complete a daily or weekly accountability check-in in under 20 seconds—and optionally activate a **Grace / Vacation Mode** window—so that taking intentional time with family pauses career streaks gracefully instead of resetting momentum to zero.

**Why this priority**: Keeps cognitive load near zero (Fiona Protocol 20-Second Rule) and prevents streak-reset discouragement during travel or family emergencies.

**Independent Test**: Enable `grace_mode=True` for an ISO week, verify active career streaks freeze rather than reset to `0`, while restorative life/family check-ins continue counting positively.

**Acceptance Scenarios**:

1. **Given** an authenticated Hero submitting `POST /api/accountability/recon-checkin`, **When** the payload contains valid `pillar_id`, `minutes_spent`, and `win_note`, **Then** the check-in is persisted atomically in MongoDB, projected into the Neo4j Identity Graph (`(:Hero)-[:LOGGED_WIN]->(:PillarCheckIn)`), and returns the refreshed streak badge.
2. **Given** a Hero with `grace_mode=True` for week `2026-W47`, **When** `2026-W47` closes with `0` career check-ins, **Then** the Hero's prior career streak is preserved (`status="paused_grace"`) instead of reset to `0`.

---

### User Story 3 - Portable Markdown Snapshot Export for Git & Mobile Review (Priority: P2)

As a Hero traveling with only a phone or Windows laptop, I want a single endpoint (`GET /api/accountability/export-markdown`) that renders my current North Star Pillars, active streaks, and recent micro-wins as clean, `markdownlint`-compliant Markdown (`<= 450` lines), so I can mirror it into `Notes_repo` or Google Drive and check my progress anywhere.

**Why this priority**: Bridges live Porter database state with the Git-backed `Notes_repo` Rosetta Stone ecosystem for offline/mobile visibility.

**Independent Test**: Call `GET /api/accountability/export-markdown` for a seeded tenant and verify valid Markdown headings, tables, zero PII/secret leakage, and accurate streak figures matching `GET /api/accountability/streaks`.

---

### Edge Cases

* **New Tenant with Zero Pillars**: Returns an empty pillar list plus optional default Nexus Starter Pillars template (`Career`, `Business/FinOps`, `Builder/Joy Fuel`, `Life & Relationship`) without raising errors.
* **Duplicate Check-In Submission (Double-Tap on Mobile)**: Deduplicated via deterministic tenant-scoped `checkin_uuid` (`user_email` + `pillar_id` + `iso_date` + `idempotency_key`).
* **Offline MongoDB / Neo4j in Local Dev**: Falls back gracefully to `mongomock` (consistent with `003-first-serving-hub-api` resilient dev fallback) and marks `graph_sync_status="PENDING_GRAPH_SYNC"`.
* **Hostile / Malformed Inputs**: Rejects null bytes (`\x00`), negative `minutes_spent`, `weekly_target_count > 21`, or XSS tags via strict Pydantic v2 boundary validation (`src/schemas/accountability_models.py`).

---

## 2. Functional Requirements *(mandatory)*

* **FR-001**: System MUST store tenant-scoped `NorthStarPillar` records keyed by `(user_email, pillar_id)` with fields: `title`, `category`, `weekly_target_count`, `target_unit`, `is_restorative_life_pillar`, `grace_eligible`, and `active`.
* **FR-002**: System MUST accept 20-Second Recon check-ins via `POST /api/accountability/recon-checkin`, validate via Pydantic v2, deduplicate via `idempotency_key`, and update weekly streak metrics deterministically without requiring external LLM inference (FinOps zero-cost rule).
* **FR-003**: System MUST compute `WeeklyStreakSummary` per pillar (`current_streak_weeks`, `longest_streak_weeks`, `completed_this_week`, `weekly_target_count`, `completion_ratio`, `streak_status`) supporting `active`, `at_risk`, `paused_grace`, and `broken` states.
* **FR-004**: System MUST treat `is_restorative_life_pillar=True` check-ins as first-class positive wins and include a balanced `life_harmony_ratio` in the aggregate dashboard payload.
* **FR-005**: System MUST provide `GET /api/accountability/export-markdown` returning sanitized, `markdownlint`-valid Markdown suitable for `Notes_repo/documentation/current-future-work/`.
* **FR-006**: All MongoDB queries MUST use explicit projections and compound indexes on `(user_email, iso_week)` / `(user_email, pillar_id)`; all Neo4j merges MUST use idempotent `MERGE` constraints and the singleton connection pool (`Bolt`).
