"""
Pydantic v2 Contracts and Data Models for the Unified Spec-Kit, Jira, and Jules Bridge.

Enforces strict input/output validation across HTTP boundaries, CLI orchestrators,
and MongoDB/Neo4j persistence layers (Constitution Principle VII.3).
"""
from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


PersonaType = Literal[
    "sentinel",
    "bolt",
    "palette",
    "archie",
    "docdoc",
    "dave",
    "crii",
    "jovol",
    "silas",
]

SyncStatus = Literal[
    "synced",
    "pending_upstream",
    "unlinked",
    "conflict",
]

IssueType = Literal["Epic", "Story", "Task", "Sub-task"]
DispatchStatus = Literal["preview", "queued", "dispatched", "failed"]


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 formatted string."""
    return datetime.now(timezone.utc).isoformat()


class SpecKitTaskItem(BaseModel):
    """
    Represents a parsed task line from `specs/NNN-feature/tasks.md`.
    Maps directly to the conceptual `Spec-Kit Task Mapping` entity.
    """
    task_id: str = Field(..., pattern=r"^T\d{3,}$")
    feature_id: str = Field(..., min_length=3, max_length=120)
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(default="", max_length=15000)
    is_parallel: bool = Field(default=False)
    user_story: Optional[str] = Field(default=None, pattern=r"^US\d+$")
    target_paths: list[str] = Field(default_factory=list)
    persona: PersonaType = Field(default="silas")
    completed: bool = Field(default=False)


class JiraIssueRecord(BaseModel):
    """
    Tracked Issue Record cached in tenant-scoped MongoDB (`jira_issues_staging`)
    and merged idempotently into the Neo4j Identity Graph (`:Quest:Intention`).
    """
    uuid: str = Field(..., min_length=32, max_length=64)
    user_email: str = Field(..., min_length=3, max_length=255)
    jira_key: str = Field(..., pattern=r"^([A-Z][A-Z0-9_]+-\d+|LOCAL-T\d{3,})$")
    project_key: str = Field(..., pattern=r"^[A-Z][A-Z0-9_]+$")
    issue_type: IssueType = Field(default="Task")
    task_id: Optional[str] = Field(default=None, pattern=r"^T\d{3,}$")
    feature_id: Optional[str] = Field(default=None, max_length=120)
    epic_key: Optional[str] = Field(default=None, max_length=64)
    summary: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=20000)
    status: str = Field(default="To Do", min_length=1, max_length=64)
    persona: PersonaType = Field(default="silas")
    labels: list[str] = Field(default_factory=list)
    sync_status: SyncStatus = Field(default="synced")
    correlation_id: str = Field(..., min_length=3, max_length=255)
    jules_session_id: Optional[str] = Field(default=None, max_length=128)
    updated_at: str = Field(default_factory=_utc_now_iso)

    @field_validator("summary", "user_email", "correlation_id")
    @classmethod
    def reject_null_bytes(cls, value: str) -> str:
        """Guard against null-byte injection in string inputs (Crii / Sentinel defense)."""
        if "\x00" in value:
            raise ValueError("Null bytes are not permitted in issue fields.")
        return value.strip()


class JulesWorkOrder(BaseModel):
    """
    Represents a structured delegation package formatted from a Jira ticket and
    Spec-Kit specification for execution via `@google/jules`.
    """
    work_order_id: str = Field(..., min_length=32, max_length=64)
    user_email: str = Field(..., min_length=3, max_length=255)
    jira_key: str = Field(..., pattern=r"^([A-Z][A-Z0-9_]+-\d+|LOCAL-T\d{3,})$")
    task_id: Optional[str] = Field(default=None, pattern=r"^T\d{3,}$")
    feature_id: str = Field(..., min_length=3, max_length=120)
    persona: PersonaType = Field(default="silas")
    playbook_path: str = Field(..., min_length=3, max_length=255)
    target_paths: list[str] = Field(default_factory=list)
    verification_commands: list[str] = Field(..., min_length=1)
    formatted_prompt: str = Field(..., min_length=20, max_length=30000)
    dry_run: bool = Field(default=True)
    dispatch_status: DispatchStatus = Field(default="preview")
    jules_session_id: Optional[str] = Field(default=None, max_length=128)
    correlation_id: str = Field(..., min_length=3, max_length=255)


class JiraSyncRequestSchema(BaseModel):
    """Request payload for POST /api/integrations/jira/sync."""
    project_key: Optional[str] = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]+$")
    jql_filter: Optional[str] = Field(default=None, max_length=1000)
    max_results: int = Field(default=50, ge=1, le=100)
    flush_pending: bool = Field(default=True)


class SpecKitPushRequestSchema(BaseModel):
    """Request payload for POST /api/integrations/jira/speckit-push."""
    feature_dir: str = Field(..., min_length=3, max_length=255)
    project_key: Optional[str] = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]+$")
    dry_run: bool = Field(default=True)


class JulesDispatchRequestSchema(BaseModel):
    """Request payload for POST /api/integrations/jules/dispatch."""
    jira_key: str = Field(..., pattern=r"^([A-Z][A-Z0-9_]+-\d+|LOCAL-T\d{3,})$")
    task_id: Optional[str] = Field(default=None, pattern=r"^T\d{3,}$")
    feature_dir: Optional[str] = Field(default=None, max_length=255)
    persona_override: Optional[PersonaType] = Field(default=None)
    dry_run: bool = Field(default=True)
