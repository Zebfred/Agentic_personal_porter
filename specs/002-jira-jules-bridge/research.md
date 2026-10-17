# Phase 0 Research: Unified Spec-Kit, Jira, and Jules Bridge

**Feature**: `002-jira-jules-bridge`
**Date**: 2026-10-17
**Spec**: [spec.md](spec.md)

---

## 1. Atlassian Jira REST API v3 & Authentication Pattern

- **Decision**: Build a lightweight, sovereign HTTP client in `src/integrations/jira_client.py` using `requests` (already in the dependency tree) against the **Atlassian Jira Cloud REST API v3** (`/rest/api/3/issue`, `/rest/api/3/search/jql`, `/rest/api/3/issue/{issueIdOrKey}/transitions`, `/rest/api/3/issue/{issueIdOrKey}/comment`) authenticated via HTTP Basic Auth (`(JIRA_EMAIL, JIRA_API_TOKEN)` loaded exclusively from `.auth/.env`), wrapped with `invoke_with_retry` from `src/utils/retry_utils.py`.
- **Rationale**:
  - Avoids introducing heavyweight third-party Atlassian SDKs that pull unnecessary transitive dependencies or obscure rate-limit status codes.
  - Directly leverages our existing Tenacity-based `invoke_with_retry` exponential backoff helper (`src/utils/retry_utils.py`) and conforms to **Sentinel** security rules (strict URL validation via `urllib.parse.urlparse`, zero hardcoded fallbacks, sanitized exceptions).
  - Supports clean offline unit testing via `unittest.mock.patch` and `mongomock` in under 10ms per test (Principle IX).
- **Alternatives Considered**:
  - *Community Spec-Kit Jira Extensions (`mbachorik/spec-kit-jira`, `Fyloss/spec-kit-jira-mirror`)*: Evaluated via `specify extension search jira`. Marked as `discovery-only` in the community catalog and lack integration with Porter's multi-tenant MongoDB staging (`jira_issues_staging`), Neo4j Identity Graph, and `.jules/*.md` persona playbooks. Building a native Porter client + local Spec-Kit hook gives us 100% zero-trust control and bi-directional graph sync.
  - *`atlassian-python-api` library*: Adds external dependency surface area for simple REST endpoints that are cleaner to type-check with our own Pydantic v2 models in `src/schemas/jira_models.py`.

---

## 2. Spec-Kit Hook & Task-to-Jira Deduplication Strategy

- **Decision**: Implement a local Spec-Kit hook and CLI orchestrator (`src/orchestrators/speckit_jira_bridge.py` + `.specify/extensions.yml` hook registration for `after_tasks` and `before_taskstoissues`) that parses `specs/NNN-feature/spec.md`, `plan.md`, and `tasks.md`.
- **Rationale**:
  - `tasks.md` uses canonical task IDs (`\bT\d{3,}\b`, e.g., `T001`, `T002`) and optional `[P]` parallel markers and `[US#]` user story tags.
  - By querying Jira via JQL (`project = "<KEY>" AND summary ~ "T001"`) and checking local MongoDB (`jira_issues_staging` projected with `{"_id": 0, "task_id": 1, "jira_key": 1}` per **Bolt** guidelines), the bridge guarantees 100% idempotent Epic and Story creation across repeated runs (`FR-006`, `SC-002`).
  - Automatic persona inference maps file paths or explicit tags in `tasks.md` to the 8 cross-cutting `.jules/<persona>.md` profiles (`sentinel`, `bolt`, `palette`, `archie`, `docdoc`, `dave`, `crii`, `jovol`) plus `silas` as final gatekeeper.
- **Alternatives Considered**:
  - *GitHub Issues only (`/speckit-taskstoissues`)*: Does not satisfy Atlassian Jira project management requirements or bidirectional sprint status synchronization.

---

## 3. Jira ↔ Jules Work Order Formatter & Dispatcher

- **Decision**: Implement `src/integrations/jules_dispatcher.py` to transform a standardized `JiraIssueRecord` (and its linked Spec-Kit `spec.md` / `plan.md` / `tasks.md` slice) into a self-contained `JulesWorkOrder` payload, supporting both `--dry-run` preview/queueing in MongoDB (`jules_work_orders`) and live CLI execution via `@google/jules` (`jules new "<formatted_prompt>"`).
- **Rationale**:
  - Google Jules operates best when given:
    1. Exact task ID, Jira key, and user story context.
    2. Target file paths and Pydantic contract boundaries.
    3. The assigned persona's operational playbook injected directly from `.jules/<persona>.md`.
    4. Mandatory verification commands (`make test-<persona>` and `make verify-done`).
  - Subprocess execution uses `subprocess.run(["jules", "new", ...], shell=False)` to prevent command injection (**Sentinel** compliance) and records the resulting session reference back to both MongoDB (`jules_work_orders`) and the Jira ticket comment/transition (`FR-008`, `FR-010`).
- **Alternatives Considered**:
  - *Manual copy-paste into `jules new`*: Prone to omitting `.jules/*.md` prevention rules or forgetting to link the Jira issue key and correlation ID.

---

## 4. Multi-Tenant & Sovereign Local Persistence Architecture

- **Decision**: Extend `UUIDGenerator` (`src/database/mongo_client/uuid_manager.py`) with `generate_for_jira_issue(jira_key: str, user_email: str)` using a dedicated namespace UUID, and persist synchronized issues via batched `bulk_write` (`ordered=False`) in `src/database/mongo_client/jira_storage.py` with explicit field projections.
- **Rationale**:
  - Complies strictly with **Principle II** (Multi-Tenant Partitioning), **Principle III** (Database Discipline & Batched `bulk_write`), and **Bolt's** playbook (explicit projection dicts, integer counts on mocks, `DESCENDING` temporal indexes).
  - Offline or rate-limited upstream writes are stored locally with `sync_status = "pending_upstream"`, preserving the **Sovereign Local Data** philosophy defined in `documentation/integrations.md`.
