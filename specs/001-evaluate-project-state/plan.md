# Implementation Plan: Evaluate Current State for Mach 4 Transition

**Branch**: `feature/spec-kit-constitution-and-documentation-rules` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-evaluate-project-state/spec.md`

## Summary

Conduct a comprehensive diagnostic evaluation of the **Agentic Personal Porter** to assess readiness for the **Mach 4 Transition ("Modeling The Life Engine")**. The technical approach audits the multi-tenant architecture and zero-trust security core, measures database connection pooling and bulk persistence health, verifies the readiness of proactive intent models (versioned intention chains in Neo4j), outlines the integration architecture for deterministic ML tools (Time Series Burnout Sensor and Reinforcement Learning Life Path Finder), and audits frontend accessibility (WCAG) and 20-Second Recon workflows.

## Technical Context

**Language/Version**: Python 3.12+ in Conda environment `agentic_porter`

**Primary Dependencies**: Flask, CrewAI / Google ADK, PyMongo, Neo4j Python Driver, Weaviate Client, Prophet / scikit-learn (target ML tools), Tailwind CSS v4

**Storage**: MongoDB (staging timeseries landing zone), Neo4j (Identity Graph & versioned intention chains), Weaviate (intuitive semantic memory), Local Filesystem (`.auth/` zero-trust configuration)

**Testing**: `pytest`, static code analysis (Silas Protocol SCA), WCAG accessibility audit checklists

**Target Platform**: Linux (Ubuntu x86_64), Google Cloud Run (billing killswitch & serverless endpoints)

**Project Type**: Multi-tier sovereign agentic system (Flask backend API + Vanilla JS/Tailwind client + Vector & Graph database cluster)

**Performance Goals**: 
- Daily Recon workflow complete in under 20 seconds ($\le 3$ clicks)
- Neo4j query latency $< 150\text{ms}$ on multi-tenant graph traversals
- MongoDB batched bulk writes without $O(n)$ network roundtrips
- Diagnostic state evaluation runs in under 30 seconds

**Constraints**: 
- Absolute zero-trust directory isolation (`.auth/` never in Git)
- Zero permanent file deletion (all outdated code archived in `.legacy_hr/`)
- All markdown documentation placed in `documentation/` using `kebab-case.md`
- No hardcoded secrets or non-constant-time comparisons (`hmac.compare_digest` mandatory)

**Scale/Scope**: Multi-tenant architecture designed to support personal and business accounts, spanning multi-year (up to 10-year) life planning horizons.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Invariant Under Evaluation | Status | Validation Notes |
| :--- | :--- | :--- | :--- |
| **I. Sovereign Privacy & Zero-Trust** | Secrets in `.auth/`; no dev fallbacks; constant-time comparison (`hmac.compare_digest`). | **PASS** | Audited startup configurations; no hardcoded keys found in production routes. |
| **II. Multi-Tenant Architecture** | Single-tenant `HERO_NAME` eradicated; `request.user_email` enforced; composite UUIDs. | **PASS** | Verified JWT tenant derivation; deterministic hashing across entities. |
| **III. Database Discipline** | Neo4j singleton pooling; MongoDB batched `bulk_write`; 1-month chunk backfills. | **PASS** | Driver singleton verified; bulk write requirement established. |
| **IV. 20-Second Recon & A11y** | $\le 3$ clicks to log/verify; explicit `aria-label` on icon buttons; semantic CSS variables. | **PASS** | UX requirements explicitly scoped; A11y checklist established. |
| **V. Non-Destructive Lifecycle** | Outdated files moved to `.legacy_hr/`; `.bk` files cleaned up; artifacts exported. | **PASS** | Active `.legacy_hr/` archive maintained and excluded in ignore files. |
| **VI. Documentation Supremacy** | Lowercase `documentation/` directory; `kebab-case.md` naming convention. | **PASS** | Governed by updated `.agent/rules/rules.md` and spec-kit constitution. |
| **VII. Verification-Gated Delivery**| Definition of Done requires test suite or checklist; no bare `except:` passes. | **PASS** | Evaluation checklist and contract schema defined in Phase 1. |
| **VIII. Preset Supremacy** | Project-local `constitution.md` takes precedence over Spec Kit fork presets. | **PASS** | Symlink `.specify/memory/constitution.md` active and intact. |

*GATE RESULT: ALL CONSTITUTIONAL PRINCIPLES PASSED.*

## Project Structure

### Documentation & Spec Artifacts (this feature)

```text
specs/001-evaluate-project-state/
├── spec.md              # Feature specification (Mach 4 transition focus)
├── plan.md              # This implementation plan
├── research.md          # Phase 0: Diagnostic findings & Mach 4 gap analysis
├── data-model.md        # Phase 1: Mach 4 Life Engine entities & evaluation data structures
├── quickstart.md        # Phase 1: Execution guide for running state checks
├── contracts/           # Phase 1: Machine-readable report schemas
│   └── mach4-evaluation-contract.json
└── checklists/          # Quality validation gates
    └── requirements.md
```

### Source Code Architecture (Target Repository Layout)

```text
src/
├── app.py                      # Primary Flask entry point (fail-secure, global CORS)
├── routes/
│   ├── auth_middleware.py      # JWT extraction & tenant propagation (request.user_email)
│   ├── journal_routes.py       # Saga status tracking & intention processing
│   ├── user_routes.py          # /api/user/hub_metrics endpoint
│   └── admin_routes.py         # Authenticated infrastructure endpoints
├── database/
│   ├── neo4j_db.py             # Singleton connection pooling & Cypher MERGE logic
│   └── mongo_storage.py        # Timeseries collections & batched bulk_write logic
├── agents/
│   ├── first_serving_porter.py # Frontline conversational agent (intent generation)
│   ├── socratic_coach.py       # Heuristic delta calculation & Fog of War detection
│   ├── audit_inspector.py      # Category verification against golden truth
│   └── ml_tools/               # Mach 4 Deterministic Tools
│       ├── burnout_sensor.py   # Time-series forecasting (Prophet/LSTM interface)
│       └── path_finder.py      # Reinforcement Learning graph pathfinder
frontend/
├── index.html                  # Main Hub (20-Second Recon & Verification Dashboard)
├── Adventure_Time_log.html     # Weekly actuals logger
├── Oracle_predictions.html     # Mach 4 Predictive engine UI
├── adventure_calendar.html     # Multi-period rolling calendar
└── js/                         # Client-side state hydration & auth wrappers
documentation/
├── architecture/               # High-level system design & spec-kit constitution
├── current_work/               # Active domain sprint trackers (active-*.md)
└── development/                # Security checklists & onboarding guides
```

**Structure Decision**: Retains the established monolithic-modular architecture with separate `src/`, `frontend/`, and `documentation/` roots. The Mach 4 ML capabilities are designed as modular tools under `src/agents/ml_tools/` to keep the agent orchestration lightweight and deterministic.

## Complexity Tracking

> *Constitution Check has zero unresolved violations.*

| Area | Decision | Rationale |
| :--- | :--- | :--- |
| **ML Models as Tools** | Integrate Prophet/RL as deterministic tools called by agents rather than embedding heavy LLM fine-tuning. | Prevents latency spikes, guarantees deterministic mathematics for Hero Numbers, and conforms to Silas efficiency guidelines. |
| **Versioned Intention Chains** | Model sequential intentions as chained Neo4j relationships rather than replacing nodes in-place. | Preserves the audit trail of daily adjustments and allows exact terminal delta calculation ($\Delta = \text{Actual} - \text{Intention}_{terminal}$). |
