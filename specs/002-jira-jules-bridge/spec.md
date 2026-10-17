# Feature Specification: Unified Spec-Kit, Jira, and Jules Bridge

**Feature Branch**: `002-jira-jules-bridge`

**Created**: 2026-10-17

**Status**: Draft

**Input**: User description: "The Unified Speckit/Jira ↔ Jules Bridge (Build the Jira read/write client first, with a hooks for standard format/creation in speckit to format/dispatch Jira tickets to Jules)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bi-Directional Jira Issue Synchronization (Read & Write Foundation) (Priority: P1)

As a project owner and daily planner, I want to read active issues and sprint assignments from my external issue tracker into my sovereign local workspace and write newly planned tasks, status transitions, and work progress back out, so that my personal daily intentions and actual completed work stay continuously aligned with my project management board without manual double-entry.

**Why this priority**: A reliable, sovereign read/write connection to the project management board is the foundational prerequisite for both personal intent/actual reconciliation and downstream automated task delegation.

**Independent Test**: Can be fully tested by executing a synchronization cycle against a simulated or live project board to pull assigned issues into local tenant storage, creating or updating an issue locally, and verifying that the upstream issue reflects the updated status and work summary without duplicating records.

**Acceptance Scenarios**:

1. **Given** an authenticated user with valid project tracker credentials, **When** the user triggers an issue pull for their active project or sprint, **Then** all matching issues are imported into the user's isolated local workspace with deterministic, collision-proof identifiers and mapped to the user's planned intentions.
2. **Given** a locally recorded work completion or status change linked to a tracked issue, **When** an upstream write synchronization runs, **Then** the corresponding external issue's status and work log are updated accurately.
3. **Given** an offline or rate-limited external tracker, **When** a user logs progress or creates a task locally, **Then** the system preserves the update locally as pending synchronization and retries safely without losing user data or blocking the user interface.

---

### User Story 2 - Spec-Kit to Jira Standardized Issue Creation Hook (Priority: P2)

As a feature architect using Spec-Driven Development, I want a standardized workflow hook that converts approved feature specifications and dependency-ordered task breakdowns into structured project management hierarchy items (Epics and child Stories/Tasks) with automatic deduplication, so that every specification phase automatically populates the project board in a uniform format.

**Why this priority**: Eliminates manual copy-pasting between specification documents and the issue tracker while guaranteeing that every ticket contains the exact specification context, acceptance criteria, and task identifier (`T001`, `T002`, etc.) required for execution.

**Independent Test**: Can be independently tested by running the task-to-issue conversion hook on a feature directory containing a specification and task list, verifying that an Epic and linked child tickets are created once, and re-running the hook to confirm zero duplicate tickets are created.

**Acceptance Scenarios**:

1. **Given** a feature directory with a completed specification and a numbered task list (`T001` through `TNNN`), **When** the Spec-Kit issue synchronization hook is invoked, **Then** the system creates or updates a parent Epic for the feature and creates standardized child tickets for each unmapped task.
2. **Given** a task list where several task identifiers (`T001`, `T002`) already exist in the target project board, **When** the synchronization hook is re-executed, **Then** existing tasks are matched by their canonical task identifier and skipped or updated in place without creating duplicates.
3. **Given** a task tagged with a specialized quality persona or parallel execution marker, **When** the standardized ticket is formatted, **Then** the ticket description and labels preserve the persona assignment, target file scope, and verification criteria.

---

### User Story 3 - Automated Formatting and Dispatch of Jira Tickets to Jules (Priority: P3)

As an engineering lead orchestrating autonomous coding agents, I want to format eligible Jira tickets (or Spec-Kit tasks linked to Jira tickets) into self-contained work orders—bundled with the feature specification context, persona operational rules, and mandatory verification gates—and dispatch them to the asynchronous coding agent (Jules), so that well-scoped tasks are executed and verified in parallel while updating ticket status automatically.

**Why this priority**: Turns static project management tickets into autonomous engineering execution while enforcing strict quality gates and persona boundaries.

**Independent Test**: Can be independently tested by selecting a standardized Jira ticket tagged for autonomous execution, running the dispatch formatter in dry-run or live mode, and verifying that the generated work order contains the ticket metadata, specification acceptance criteria, persona operational rules, and quality verification commands, and records the dispatch reference back onto the ticket.

**Acceptance Scenarios**:

1. **Given** a standardized Jira ticket linked to a Spec-Kit task and assigned to a specialized agent persona, **When** the user or workflow hook dispatches the ticket to Jules, **Then** the system assembles a complete work order prompt containing the issue summary, specification constraints, persona playbook rules, and required verification checks.
2. **Given** a successfully dispatched work order, **When** the asynchronous coding session is initiated, **Then** the corresponding Jira ticket is transitioned or annotated with the active session reference so the user has full transparency into delegated work.
3. **Given** a ticket that lacks required specification context or fails pre-dispatch validation, **When** dispatch is attempted, **Then** the system blocks the dispatch with a clear, actionable diagnostic message explaining which prerequisite field or acceptance criterion is missing.

---

### Edge Cases

- **Duplicate Synchronization Runs**: What happens when the Spec-Kit-to-Jira hook or Jira pull is triggered multiple times in rapid succession? The system must enforce strict idempotency using canonical task identifiers (`T001`+) and composite tenant-scoped keys so duplicate issues or graph nodes are never created.
- **External Tracker Rate Limiting or Outages**: How does the system handle HTTP 429 rate limits or temporary network unavailability from the issue tracker or asynchronous coding agent? Requests must use exponential backoff with jitter, and failed upstream writes must remain queued locally with a clear synchronization status rather than failing silently.
- **Malformed or Incomplete Credentials**: What happens when tracker credentials or project keys are missing or invalid? The client must fail fast with an explicit, sanitized configuration error without exposing sensitive tokens in logs or responses.
- **Orphaned or Deleted Remote Issues**: What happens if an issue previously linked to a local task is deleted or moved to an inaccessible project remotely? Synchronization must log a clear reconciliation warning and mark the local record as unlinked rather than crashing the batch pipeline.
- **Unassigned or Unknown Persona Tags**: What happens when a ticket is queued for Jules dispatch without a recognized persona tag? The formatter must default to the baseline quality gatekeeper profile and require standard verification checks before completion.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a bi-directional issue tracker client capable of reading issues, sprints, and statuses, as well as creating issues, updating descriptions/fields, transitioning workflow states, and appending work comments.
- **FR-002**: System MUST isolate all credentials, API tokens, and endpoint configurations within the zero-trust `.auth/` boundary and fail fast with a clear diagnostic message if required credentials are absent.
- **FR-003**: System MUST scope all locally cached issues and intention/actual mappings to the authenticated user's tenant identity (`user_email`) using deterministic composite identifiers.
- **FR-004**: System MUST batch local persistence operations during multi-issue synchronization to prevent iterative single-record database roundtrips.
- **FR-005**: System MUST provide a standardized Spec-Kit synchronization hook that parses `spec.md`, `plan.md`, and `tasks.md` from the active feature directory and formats them into a consistent Epic and child Task/Story payload.
- **FR-006**: System MUST deduplicate tasks during Spec-Kit-to-Jira synchronization by matching canonical task identifiers (`\bT\d{3,}\b`) and feature keys across both open and closed issues in the target project.
- **FR-007**: System MUST enrich formatted Jira tickets and Jules work orders with the applicable quality persona profile (`sentinel`, `bolt`, `palette`, `archie`, `docdoc`, `dave`, `crii`, `jovol`, or `silas`) based on task labels or file-domain mapping.
- **FR-008**: System MUST provide a Jules bridge dispatcher that transforms a standardized Jira ticket (or linked Spec-Kit task) into a structured asynchronous agent work order containing: (a) the issue objective and acceptance criteria, (b) target file paths, (c) the assigned persona's prevention rules, and (d) the mandatory verification command suite.
- **FR-009**: System MUST support a dry-run preview mode for both Spec-Kit-to-Jira creation and Jira-to-Jules dispatch so users can inspect formatted payloads before mutating remote systems or launching remote agent sessions.
- **FR-010**: System MUST record lineage metadata (linking the Spec-Kit task ID, the Jira issue key, the local correlation ID, and the Jules session reference) so work can be traced end-to-end across all three systems.

### Key Entities

- **Tracked Issue Record (`JiraIssueRecord`)**: Represents a synchronized project management issue stored locally, including its external issue key (e.g., `PROJ-123`), canonical Spec-Kit task ID (e.g., `T001`), summary, description, status, assigned persona label, tenant owner, and synchronization state (`synced`, `pending_upstream`, `conflict`).
- **Spec-Kit Task Mapping (`SpecKitTaskItem`)**: Represents the link between a feature directory (`specs/NNN-feature/`), its parent Epic key in the issue tracker, and the mapping of individual `tasks.md` items to remote issue keys.
- **Jules Work Order (`JulesWorkOrder`)**: Represents a structured delegation package formatted from a Jira ticket and Spec-Kit specification, containing the task prompt, persona playbook directives, target verification gate, and execution status/session identifier.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can synchronize an entire feature specification's task list (`tasks.md`) into standardized, hierarchy-linked Jira issues in under 15 seconds for a 25-task feature.
- **SC-002**: 100% of repeated synchronization runs on the same `tasks.md` file produce zero duplicate Jira issues and zero duplicate local intention nodes.
- **SC-003**: 100% of work orders dispatched through the Jira-to-Jules bridge automatically include the target task acceptance criteria, the mapped persona playbook rules, and the required verification gate command.
- **SC-004**: Local unit and contract verification of the entire read/write client, Spec-Kit hook formatter, and Jules dispatcher executes completely offline in under 2 seconds with $0.00 external cloud or API cost.
- **SC-005**: When an external issue tracker returns transient rate-limit or network errors, 100% of local user updates are preserved in a pending synchronization state with zero data loss.

## Assumptions

- Users have access to an Atlassian Jira Cloud (or compatible REST API) project and can supply an API token, account email, base URL, and default project key in `.auth/.env`.
- Spec-Kit feature specifications follow the repository's standard directory structure (`specs/NNN-feature/spec.md`, `plan.md`, `tasks.md`) with task identifiers formatted as `T001`, `T002`, etc.
- Google Jules CLI (`@google/jules`) is the target interface for asynchronous coding session dispatch, and the dispatcher will support both live CLI invocation and structured dry-run/queue output when the CLI is not actively authenticated.
- Local storage remains the authoritative source of truth for the user's personal reflections and identity graph, in accordance with the Sovereign Local Data architecture.
