# Phase 1 Data Model: First-Serving Agent API, Porter Hub Support & Jira/Jules GUI (`003-first-serving-hub-api`)

**Feature Branch**: `003-first-serving-hub-api`  
**Date**: 2026-10-25  
**Schema Module**: `src/schemas/hub_models.py` (and extensions to `src/schemas/jira_models.py`)

---

## 1. Domain & Boundary Schemas (`src/schemas/hub_models.py`)

### 1.1 `SagaStatusType` (Literal)
Allowed pipeline saga states for journal and planning records:
- `"RECEIVED"` — Persisted in MongoDB landing zone, awaiting downstream processing.
- `"LLM_PROCESSING"` — Currently undergoing Socratic Mirror / First-Serving Porter analysis.
- `"GRAPH_INJECTED"` — Synchronized into the Neo4j Identity Graph (`:Hero`, `:Week`, `:Intention`, `:LogEntry`).
- `"FAILED"` — Downstream graph or LLM step failed (sanitized error details recorded).

### 1.2 `EventToBeClassified` (Pydantic BaseModel)
Represents a raw calendar event staged in `events_to_be_classified` (`MongoConfig.EVENTS_TO_BE_CLASSIFIED_COLLECTION`) awaiting Hero or agent triage.
- `uuid`: `str` — Deterministic tenant-scoped UUIDv5 (`UUIDGenerator.generate_for_event(gcal_id, user_email)`).
- `user_email`: `str` — Authenticated tenant email (`min_length=3`).
- `gcal_id`: `str` — Source Google Calendar event ID (`min_length=1`).
- `summary`: `str` — Event title/summary (`min_length=1`, `max_length=500`).
- `start_time`: `str` — ISO-8601 start timestamp.
- `end_time`: `Optional[str]` — ISO-8601 end timestamp.
- `suggested_pillar`: `Optional[str]` — Candidate Maslow/Ambition pillar suggested by GTKY classifier.
- `confidence_score`: `int` — Classifier confidence `0..100` (default `50`).
- `status`: `Literal["pending_classification", "classified", "dismissed"]` (default `"pending_classification"`).
- `correlation_id`: `str` — Cross-system lineage ID.

### 1.3 `HubProgressMetrics` (Pydantic BaseModel)
Returned by `GET /api/user/hub_metrics` (and `GET /api/calendar/adventure_log` under `data`):
- `user_email`: `str`
- `intentions`: `int = Field(ge=0)` — Count of logged intentions (`event_intentions`).
- `calendar_events`: `int = Field(ge=0)` — Count of logged actual/unified calendar events (`event_actuals` + `unified_events`).
- `unclassified`: `int = Field(ge=0)` — Count of pending items in `events_to_be_classified` (plus any staged raw events).
- `matched`: `int = Field(ge=0)` — Count of matched intentions (`unified_events`).
- `valuable_detours`: `int = Field(ge=0)` — Count of valuable detours (`event_actuals` where `actual.detour_type == "valuable"`).
- `detrimental_detours`: `int = Field(ge=0)` — Count of detrimental detours (`event_actuals` where `actual.detour_type == "detrimental"`).
- `detrimental_improvement_pct`: `float` — Week-over-week percentage reduction in detrimental detours (`0.0` when prior week is `0`).
- `detrimental_delta`: `str` — Formatted UI badge (e.g., `"↓ 25%"`, `"↑ 10%"`, or `"↓ 0%"`).

### 1.4 `WeeklyIntentionItem` & `WeeklyPlanningRequestSchema` (Pydantic BaseModel)
Accepted by `POST /api/planning`:
- `week_start_date`: `str` — ISO date `^\d{4}-\d{2}-\d{2}$`.
- `expectation_text`: `Optional[str]` — Natural-language or bulleted weekly intentions summary (`max_length=10000`).
- `intentions`: `list[WeeklyIntentionItem] = Field(default_factory=list)` — Optional explicit list of structured intention items (`title`, `pillar`, `day`, `time_chunk`, `priority`).
- Validation invariant: At least one of `expectation_text` (non-empty) or `intentions` (non-empty list) MUST be provided, and no string field may contain null bytes (`\x00`).

### 1.5 `ArtifactGapItem` & `ArtifactGapReport` (Pydantic BaseModel)
Returned by `GTKYIdentityArchitect.scan_missing_artifacts()` and `GET /api/artifacts/scan`:
- `artifact_name`: `Literal["hero_origin.json", "hero_ambition.json"]`
- `field_path`: `str` — JSON path or epoch/section identifier (e.g., `"origin_story.epochs[0].experiences[0]"` or `"ambition.primary_quest"`).
- `prompt`: `str` — Human-readable discovery prompt (`"- Empty slot in ..."`).
- `ArtifactGapReport`:
  - `status`: `Literal["success"] = "success"`
  - `has_gaps`: `bool`
  - `gaps`: `list[ArtifactGapItem]`
  - `results`: `str` — Formatted newline-delimited bullet string consumed by `frontend/js/user_hub.js`.

### 1.6 `HistoricalJournalRecord` (Pydantic BaseModel)
Returned in the `data` list of `GET /api/journal/history`:
- `type`: `Literal["journal", "expectation", "time_chunk"]`
- `date`: `str`
- `text`: `str`
- `correlation_id`: `str`
- `updated_at`: `Optional[str]`
- `saga_status`: `SagaStatusType` (default `"GRAPH_INJECTED"` for synced records, `"RECEIVED"` for newly saved records).
- `reflection`: `Optional[str]` — Linked Socratic reflection text if available.

### 1.7 `JiraJulesBridgeStatus` (Pydantic BaseModel)
Returned by `GET /api/integrations/jira/status` to power the Porter Hub GUI Command Center:
- `status`: `Literal["success"] = "success"`
- `feature_id`: `str` — Active Spec-Kit feature directory name (e.g., `"003-first-serving-hub-api"`).
- `jira_configured`: `bool` — Whether `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN` are set in `.auth/.env`.
- `jules_cli_available`: `bool` — Whether `JulesDispatcher._resolve_jules_binary()` locates an executable `jules` binary.
- `speckit_tasks`: `list[SpecKitTaskItem]` — Parsed tasks from the active `tasks.md` (or fallback feature).
- `staged_jira_issues`: `list[JiraIssueRecord]` — Tenant-scoped Jira issues in `jira_issues_staging`.
- `recent_work_orders`: `list[JulesWorkOrder]` — Tenant-scoped recent work orders in `jules_work_orders`.

---

## 2. MongoDB Collections & Indexes (`src/config.py`)

| Constant | Collection Name | Compound Indexes | Query Projection Pattern |
| :--- | :--- | :--- | :--- |
| `EVENTS_TO_BE_CLASSIFIED_COLLECTION` | `"events_to_be_classified"` | `(user_email, status, start_time -1)`, `(uuid) UNIQUE` | `{"_id": 0, "uuid": 1, "user_email": 1, "gcal_id": 1, "summary": 1, "start_time": 1, "suggested_pillar": 1, "confidence_score": 1, "status": 1, "correlation_id": 1}` |
| `INTENT_COLLECTION` | `"event_intentions"` | `(user_id, time_slot.start -1)` | `{"_id": 0, "user_id": 1, "title": 1, "week_start_date": 1, "correlation_id": 1}` |
| `ACTUAL_COLLECTION` | `"event_actuals"` | `(user_id, time_slot.start -1)` | `{"_id": 0, "user_id": 1, "actual.detour_type": 1, "time_slot.start": 1}` |
| `JIRA_STAGING_COLLECTION` | `"jira_issues_staging"` | `(user_email, project_key, task_id)` | Explicit projection via `JiraStorage.ISSUE_PROJECTION` |
| `JULES_WORK_ORDERS_COLLECTION` | `"jules_work_orders"` | `(user_email, task_id, dispatch_status)` | Explicit projection `{"_id": 0, ...}` |
