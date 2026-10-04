# Feature Specification: Evaluate Current State for Mach 4 Transition

**Feature Branch**: `feature/spec-kit-constitution-and-documentation-rules`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "Evaluate current state of the Agentic_personal_porter project for Mach 4 transition"

---

## Strategic Vision: The Mach 4 Transition

The **Mach 4 Lifecycle ("Modeling The Life Engine")** transitions the Agentic Personal Porter from a reactive daily logger and reflection tool (Mach 2/3) into a **proactive predictive intelligence engine** capable of steering long-term (10-year) life trajectories. 

This evaluation assesses the system's baseline readiness across:
1. **Multi-Tenant Foundation & Sovereign Data**: Zero-trust `.auth/` layer, tenant-partitioned MongoDB timeseries, and versioned Neo4j intention trees.
2. **The "Pillar Balancer" Engine**: Algorithmic scoring of daily/weekly actuals against long-term ambitions (`hero_future.json`) to compute numeric "Hero Numbers."
3. **Integrated ML Agent Tools**: Deterministic analytical tools (Time Series Burnout Sensor, Reinforcement Learning Life Path Finder) called by autonomous agent coordinators.
4. **Three Echelons of Review**: Daily triage, weekly CrewAI reflection, and monthly macro-trajectory analysis ("The Grand Visionary").
5. **High-Fidelity Hero UI**: 20-Second Recon Loop, Adventure Expectations, and predictive visualization screens (`Oracle_predictions.html`, `adventure_calendar.html`).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Tenant Core & Ingestion Baseline Audit (Priority: P1)

As a system owner, I want to evaluate our multi-tenant data pipelines and database connection pooling to verify that our MongoDB timeseries collections and Neo4j graph instances provide a stable, zero-trust foundation for Mach 4 multi-year projections.

**Why this priority**: Mach 4 predictive models require clean, uncorrupted historical timeseries and collision-proof tenant partitioning. Without robust multi-tenancy and connection pooling, advanced ML models will ingest noisy or contaminated data.

**Independent Test**: Execute an automated verification audit scanning route middlewares, MongoDB timeseries collections, Neo4j singleton pooling, and `.auth/` zero-trust compliance, reporting health status and zero cross-tenant leakage.

**Acceptance Scenarios**:
1. **Given** the active routing layer, **When** evaluating authentication and tenant context propagation, **Then** all requests derive identity strictly from `request.user_email` and fail fast if secrets are missing.
2. **Given** the database layer, **When** testing Neo4j driver lifecycle, **Then** connection pooling operates as a singleton without per-request driver closures.
3. **Given** timeseries storage in MongoDB, **When** evaluating event updates, **Then** all operations execute via batched `bulk_write` rather than sequential roundtrips.

---

### User Story 2 - Proactive Intent & "Pillar Balancer" Readiness (Priority: P2)

As the Hero (user), I want the system to evaluate how effectively the First-Serving Porter and backend can compare daily logged actuals against my long-term ambition models (`hero_future.json`) to calculate actionable "Hero Numbers" and proactively recommend weekly intent quotas.

**Why this priority**: This bridges reactive logging into the proactive Mach 4 mandate, allowing agents to intervene before detriment tasks consume high-priority life pillars.

**Independent Test**: Run a mock intention-evaluation cycle computing the numeric delta ($\Delta = \text{Actual} - \text{Intention}_{terminal}$) against versioned intention chains in Neo4j, checking algorithm output and priority recommendations.

**Acceptance Scenarios**:
1. **Given** versioned intention chains in Neo4j (`:Intention {version, created_at}`), **When** evaluating weekly delta calculations, **Then** the system computes variance against the terminal intention in the chain.
2. **Given** long-term pillar targets, **When** a critical pillar falls below quota, **Then** the evaluation validates that the First-Serving Porter generates proactive compensation blocks.

---

### User Story 3 - Integrated Machine Learning Tools Readiness (Priority: P3)

As an ML/AI engineer, I want to assess the system readiness for integrating deterministic machine learning tools (Time Series Forecasting for the "Burnout Sensor" and Reinforcement Learning for the "Life Path Finder") into the agent toolchain.

**Why this priority**: In Mach 4, agents do not guess life trajectories; they query deterministic ML models (`get_burnout_risk`, `calculate_path_to_milestone`) as standardized tool calls.

**Independent Test**: Audit feature store extraction from MongoDB timeseries, testing dataset generation for Prophet/LSTM models and state/action/reward representations for Neo4j graph traversal.

**Acceptance Scenarios**:
1. **Given** sleep gaps and task density data in MongoDB, **When** extracting timeseries features, **Then** the system produces normalized numerical arrays suitable for time series forecasting.
2. **Given** long-term milestone nodes in Neo4j, **When** formulating pathfinding problems, **Then** graph transitions are mapped to structured state-action-reward representations.

---

### User Story 4 - Echelons of Review & Predictive UX Evaluation (Priority: P4)

As a frontend architect and end-user, I want to evaluate the user interface against the 20-Second Recon Loop, WCAG accessibility, and predictive layout screens (`Oracle_predictions.html`, `Adventure_calendar.html`, and `journal_review.html`).

**Why this priority**: The 10-year predictive engine requires clear visual affordances that do not induce cognitive fatigue or violate the 20-second administrative limit.

**Independent Test**: Run an automated DOM and accessibility audit across the frontend pages, measuring click depth, ARIA attribute completeness, and local storage state hydration.

**Acceptance Scenarios**:
1. **Given** daily verification flows on `index.html`, **When** confirming inferences or logging actuals, **Then** the workflow requires no more than 3 user clicks.
2. **Given** navigation controls and modal buttons, **When** evaluated for accessibility, **Then** 100% of icon-only elements provide descriptive `aria-label` tags.
3. **Given** predictive placeholder pages (`Oracle_predictions.html`), **When** inspected for architecture readiness, **Then** component slots for ML recommendations and macro-trend graphs are identified.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST audit multi-tenant partitioning across all routes, confirming dynamic derivation of `user_email` and composite UUID generation (`UUIDGenerator.generate_for_event`).
- **FR-002**: System MUST evaluate zero-trust configuration, verifying that all secrets reside in `.auth/` and fail-secure startup prevents boot on missing keys.
- **FR-003**: System MUST verify constant-time evaluation (`hmac.compare_digest`) for all authentication tokens and API keys.
- **FR-004**: System MUST evaluate Neo4j graph driver management to guarantee singleton connection pooling and idempotent `MERGE` persistence.
- **FR-005**: System MUST audit MongoDB operations to enforce batched `bulk_write` updates and compound indices on `(user_email, start_time)`.
- **FR-006**: System MUST evaluate the schema of versioned intention chains (`(:Day)-[:PLANNED_AT]->(:Intention)`) for terminal delta calculation.
- **FR-007**: System MUST assess readiness for the "Burnout Sensor" tool by verifying timeseries data extraction pipelines from MongoDB.
- **FR-008**: System MUST evaluate agent orchestration defenses, ensuring exponential backoff decorators and state tracing (`first_serving_traces`) exist to prevent infinite loops.
- **FR-009**: System MUST audit frontend accessibility, ensuring WCAG compliance (`aria-label` on icon buttons, label-input bindings, visible keyboard focus rings).
- **FR-010**: System MUST verify that daily actual verification satisfies the 20-Second Recon Loop ($\le 3$ clicks).
- **FR-011**: System MUST audit project documentation, enforcing lowercase `documentation/` storage and `kebab-case.md` file naming.
- **FR-012**: System MUST verify that outdated files are non-destructively archived in `.legacy_hr/`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Complete 100% diagnostic coverage of the 5 Mach 4 readiness dimensions (Tenancy/Security, Ingestion/Graph, Proactive Intent Engine, ML Agent Tools, Predictive UX/A11y).
- **SC-002**: Assessment audit script runs and produces a structured readiness report in under 30 seconds in local environments.
- **SC-003**: Zero hardcoded credentials, single-tenant environment variables (`HERO_NAME`), or non-constant-time comparisons remain undetected.
- **SC-004**: Timeseries feature extraction for the Burnout Sensor produces valid feature matrices from MongoDB in under 5 seconds.
- **SC-005**: 100% of interactive frontend elements audited for accessible labeling and $\le 3$-click recon speed.
- **SC-006**: Output diagnostic deliverables comply with project documentation standards (`documentation/` with `kebab-case.md`).

---

## Assumptions

- The evaluation is performed in read-only analysis mode without mutating production or test data.
- The Mach 4 transition builds directly upon the Mach 2/3 ingestion and multi-tenant foundations.
- Local instances of MongoDB, Neo4j, and Python 3.12 (`agentic_porter` conda environment) are available for inspection.
