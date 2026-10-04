# Feature Specification: Evaluate Current State of the Agentic Personal Porter Project

**Feature Branch**: `feature/spec-kit-constitution-and-documentation-rules`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "Evaluate current state of the Agentic_personal_porter project"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Tenant Security & Sovereign State Audit (Priority: P1)

As a system owner or security auditor, I want a comprehensive evaluation of the multi-tenant architecture, data privacy boundaries, and authentication subsystems to verify that legacy single-tenant hardcoding is eradicated, sensitive credentials are safe under zero-trust rules, and no cross-tenant data leakage is possible.

**Why this priority**: Security, tenant isolation, and zero-trust privacy are fundamental, non-negotiable requirements under Principles I and II of the Constitution. Any regression at this layer endangers user data and system viability.

**Independent Test**: Can be verified by executing an automated audit inspection against API endpoints, authentication middleware, and database indices, confirming zero hardcoded credentials, timing-attack-safe comparisons, and active multi-tenant partitioning.

**Acceptance Scenarios**:

1. **Given** the backend routing and data layer, **When** scanning for legacy single-tenant environment lookups, **Then** the system confirms zero dependencies on deprecated global identifiers and verifies that tenant identity is derived strictly from verified request tokens.
2. **Given** incoming API requests, **When** evaluating authentication middleware, **Then** all protected endpoints enforce valid tenant credentials and prevent unauthenticated compute triggers or access to operational resources.
3. **Given** authentication and token comparison logic, **When** verifying secret evaluation, **Then** all credential comparisons execute using constant-time evaluation to eliminate timing side-channels.

---

### User Story 2 - Ingestion & Persistence Pipeline Health Assessment (Priority: P2)

As a data engineer or platform developer, I want to evaluate the operational health, idempotency, and throughput of data ingestion pipelines moving user calendar events through the landing zone and into the primary graph and vector memories.

**Why this priority**: Data persistence is the core engine of the Mach 2 ecosystem. The system must ingest events accurately and idempotently without exhausting rate limits, causing network roundtrip bottlenecks, or corrupting graph topology.

**Independent Test**: Can be verified by running a connectivity and pipeline inspection script checking MongoDB collections, Neo4j singleton pool status, index validity, and batch ingestion constraints.

**Acceptance Scenarios**:

1. **Given** the database connection manager, **When** evaluating Neo4j connection lifecycle, **Then** the driver is verified to run as a persistent singleton without per-request driver instantiation or destructive teardown hooks.
2. **Given** the Google Calendar backfill ingestion process, **When** checking batch chunking rules, **Then** the ingestion queue restricts batch backfills to chronological chunks of at most one month per cycle.
3. **Given** database write operations in MongoDB, **When** reviewing update execution patterns, **Then** repetitive updates are executed via batched bulk operations rather than iterative sequential network roundtrips.

---

### User Story 3 - Agent Cluster & Orchestration Readiness (Priority: P3)

As an AI workflow architect, I want to evaluate the readiness, schema alignment, and stability of the multi-agent cluster (First-Serving Porter, Socratic Mirror, GTKY Classifier, Silas Auditor, Fiona Architect, and Bill FinOps) to prevent infinite reasoning loops and ensure resilient downstream handoffs.

**Why this priority**: Unchecked agent execution can cause token explosion and service disruption. Agent payloads must strictly match downstream schema expectations.

**Independent Test**: Can be verified by inspecting agent registry definitions, observability traces, token limit decorators, and schema output contracts against active test fixtures.

**Acceptance Scenarios**:

1. **Given** the agent orchestration pipeline, **When** evaluating high-frequency task delegation, **Then** the system enforces rate-limiting backoff decorators and state tracing to prevent infinite execution loops.
2. **Given** calendar classification agents, **When** producing formatted event payloads, **Then** outputs match the strict schema required for graph injection without failing back to dry-run placeholders.
3. **Given** First-Serving Porter interactions, **When** checking user origin and ambition profiles, **Then** the agent prompts for missing fields without generating ungrounded historical claims.

---

### User Story 4 - Frontend Recon & Accessibility Compliance Audit (Priority: P4)

As a frontend architect and end-user ("Hero"), I want to evaluate the client interface against the 20-Second Recon Loop, WCAG accessibility standards, and semantic design tokens to ensure frictionless, high-fidelity daily verification.

**Why this priority**: The user interface is the daily touchpoint. High cognitive friction, broken keyboard accessibility, or desynchronized local state directly undermines the habit of daily verification.

**Independent Test**: Can be verified by running automated static code analysis across frontend templates and scripts to audit click counts, ARIA attributes, label associations, and local storage state synchronization.

**Acceptance Scenarios**:

1. **Given** interactive buttons and controls across the interface, **When** inspecting icon-only navigation and modal buttons, **Then** each element provides an explicit, descriptive accessible label.
2. **Given** primary logging workflows, **When** a user verifies or logs an actual activity, **Then** the user can complete the action within three clicks or fewer.
3. **Given** client-side state in local storage, **When** activities are updated or verified, **Then** local storage state maintains parity with backend graph updates.

---

### Edge Cases

- How does the evaluation handle unconfigured or offline local services (e.g., local Neo4j or MongoDB instances temporarily down during developer evaluation)?
  - System must report clear, non-crashing diagnostic statuses ("Service Unavailable", "Missing Env") with actionable setup steps.
- What happens if sensitive credentials are missing from `.auth/.env`?
  - Evaluation must highlight missing required variables immediately without printing or logging any existing secret values.
- How does the evaluation assess large volumes of legacy historical calendar events?
  - Diagnostic tools must sample or summarize pipeline statistics without initiating costly full-table scans.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an evaluation mechanism that audits backend routes, ensuring every protected endpoint extracts and validates tenant identity (`user_email`) from request authentication.
- **FR-002**: System MUST inspect codebase configuration to verify that no cryptographic secrets or API keys use hardcoded dev fallbacks, enforcing fail-secure startup behavior.
- **FR-003**: System MUST verify that all secret and token comparison routines utilize constant-time comparison methods (`hmac.compare_digest`).
- **FR-004**: System MUST evaluate database driver instantiation to confirm that Neo4j uses a singleton connection pool and does not attach driver closure to per-request web teardown hooks.
- **FR-005**: System MUST verify that database update routines in MongoDB leverage batched bulk writes (`bulk_write`) rather than iterative sequential network roundtrips.
- **FR-006**: System MUST evaluate calendar synchronization logic to confirm that historical ingestion is bounded to chronological chunks of at most one month.
- **FR-007**: System MUST assess agent delegation pipelines to verify the presence of token density monitoring, exponential backoff decorators, and execution tracing.
- **FR-008**: System MUST audit agent output payloads to ensure schema compatibility with the downstream formatted events pipeline.
- **FR-009**: System MUST inspect frontend HTML and JavaScript to verify WCAG accessibility compliance (explicit `aria-label` attributes on icon-only buttons, associated labels on all form inputs and textareas, and visible keyboard focus rings).
- **FR-010**: System MUST verify that frontend UI workflows for logging actual activities require no more than three user clicks (20-Second Recon Loop).
- **FR-011**: System MUST verify that project documentation is maintained in lowercase `documentation/` using `kebab-case.md` file naming, with no markdown in the project root other than `README.md`.
- **FR-012**: System MUST confirm that file retention policies preserve outdated files in `.legacy_hr/` and that `.legacy_hr/` is excluded from version control and AI token contexts.

---

### Key Entities *(include if feature involves data)*

- **Evaluation Report**: Structured assessment output capturing pass/warn/fail status, diagnostic findings, and remediation guidance across all evaluated architectural dimensions.
- **System Dimension**: Specific architectural domain under evaluation (Multi-Tenant Security, Data Pipeline & Persistence, Agent Orchestration, Frontend UX & A11y, Documentation & Hygiene).
- **Audit Check**: Individual testable invariant verified during the evaluation with associated severity (Critical, Warning, Informational).
- **Remediation Item**: Actionable technical task identified during evaluation to bring an invariant into full constitutional compliance.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Evaluation covers 100% of the five constitutional pillars (Security/Tenancy, Database Discipline, Agent Orchestration, Frontend Recon/A11y, Documentation Hygiene).
- **SC-002**: Audit check completes execution and generates a diagnostic report in under 30 seconds in local development environments.
- **SC-003**: Zero hardcoded secrets, single-tenant environment variables (`HERO_NAME`), or insecure string comparisons (`==` on tokens) remain undetected.
- **SC-004**: 100% of icon-only interactive frontend elements and form fields are audited for WCAG accessibility labeling.
- **SC-005**: The evaluation output produces clear, prioritized remediation items mapping directly to the active sprint backlog documents (`documentation/current_work/active-*.md`).
- **SC-006**: The evaluation report itself adheres to the project's documentation standards (located in `documentation/` using `kebab-case.md`).

---

## Assumptions

- Target developers and auditors run evaluations in an environment with access to project source files and local test configurations.
- Production services and live credentials are evaluated safely without exposing secret keys in logs, terminal outputs, or artifacts.
- Evaluation tools operate in read-only analysis mode during assessment, preventing destructive state modification of databases or user data.
- The evaluation respects the active Conda environment (`agentic_porter`) and `uv` package workspace definitions.
