"""
Pydantic v2 Domain & Boundary Contracts for First-Serving Hub API (`003-first-serving-hub-api`).

Enforces strict type validation, null-byte defense (`Crii`/`Sentinel`), and
contract-first typing (`Archie`) across Hub Progress Metrics, Classification
Queue, One-Shot Weekly Planning, Missing Artifact Discovery, Historical Journal
Saga Status, and the Jira <-> Jules Bridge Hub GUI Status.
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator

from src.schemas.jira_models import JiraIssueRecord, JulesWorkOrder, SpecKitTaskItem

SagaStatusType = Literal["RECEIVED", "LLM_PROCESSING", "GRAPH_INJECTED", "FAILED"]
ClassificationStatusType = Literal["pending_classification", "classified", "dismissed"]


def _reject_null_bytes(value: Any) -> Any:
    """Recursively reject null bytes in string payloads."""
    if isinstance(value, str) and "\x00" in value:
        raise ValueError("Null bytes are not permitted in string fields.")
    if isinstance(value, list):
        for item in value:
            _reject_null_bytes(item)
    elif isinstance(value, dict):
        for k, v in value.items():
            _reject_null_bytes(k)
            _reject_null_bytes(v)
    return value


class EventToBeClassifiedInput(BaseModel):
    """Input item for staging raw calendar events into `events_to_be_classified`."""

    gcal_id: str = Field(..., min_length=1, max_length=256)
    summary: Optional[str] = Field(default=None, max_length=500)
    title: Optional[str] = Field(default=None, max_length=500)
    start_time: str = Field(..., min_length=4, max_length=64)
    end_time: Optional[str] = Field(default=None, max_length=64)
    suggested_pillar: Optional[str] = Field(default="Uncategorized", max_length=120)
    confidence_score: int = Field(default=50, ge=0, le=100)

    @model_validator(mode="after")
    def normalize_summary(self) -> "EventToBeClassifiedInput":
        resolved = (self.summary or self.title or "").strip()
        if not resolved:
            raise ValueError("Either summary or title must be provided.")
        self.summary = resolved
        return self


class ClassificationQueueRequestSchema(BaseModel):
    """Request payload for `POST /api/calendar/classification_queue`."""

    source: str = Field(default="gcal_sync", max_length=64)
    events: list[EventToBeClassifiedInput] = Field(..., min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_no_nulls(self) -> "ClassificationQueueRequestSchema":
        _reject_null_bytes(self.model_dump())
        return self


class EventToBeClassified(BaseModel):
    """Persisted record in `events_to_be_classified`."""

    uuid: str = Field(..., min_length=8, max_length=64)
    user_email: str = Field(..., min_length=3, max_length=254)
    gcal_id: str = Field(..., min_length=1, max_length=256)
    summary: str = Field(..., min_length=1, max_length=500)
    start_time: str = Field(..., min_length=4, max_length=64)
    end_time: Optional[str] = Field(default=None, max_length=64)
    suggested_pillar: Optional[str] = Field(default="Uncategorized", max_length=120)
    confidence_score: int = Field(default=50, ge=0, le=100)
    status: ClassificationStatusType = Field(default="pending_classification")
    correlation_id: str = Field(..., min_length=4, max_length=128)


class HubProgressMetrics(BaseModel):
    """Aggregated telemetry returned by `GET /api/user/hub_metrics`."""

    user_email: str = Field(..., min_length=3, max_length=254)
    intentions: int = Field(default=0, ge=0)
    calendar_events: int = Field(default=0, ge=0)
    unclassified: int = Field(default=0, ge=0)
    matched: int = Field(default=0, ge=0)
    valuable_detours: int = Field(default=0, ge=0)
    detrimental_detours: int = Field(default=0, ge=0)
    detrimental_improvement_pct: float = Field(default=0.0)
    detrimental_delta: str = Field(default="↓ 0%")


class WeeklyIntentionItem(BaseModel):
    """Single intention block within a one-shot weekly planning submission."""

    title: str = Field(..., min_length=1, max_length=500)
    pillar: str = Field(default="General", min_length=1, max_length=120)
    day: Optional[str] = Field(default=None, max_length=32)
    start_date: Optional[str] = Field(default=None, max_length=32)
    time_chunk: Optional[str] = Field(default=None, max_length=64)
    duration_minutes: int = Field(default=60, ge=5, le=1440)
    priority: str = Field(default="P2", max_length=32)


class WeeklyPlanningRequestSchema(BaseModel):
    """Request payload for `POST /api/planning`."""

    week_start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    expectation_text: Optional[str] = Field(default=None, max_length=10000)
    expectation_summary: Optional[str] = Field(default=None, max_length=10000)
    intentions: list[WeeklyIntentionItem] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_content_and_nulls(self) -> "WeeklyPlanningRequestSchema":
        _reject_null_bytes(self.model_dump())
        if not self.expectation_text and self.expectation_summary:
            self.expectation_text = self.expectation_summary
        has_text = bool(self.expectation_text and self.expectation_text.strip())
        if not has_text and not self.intentions:
            raise ValueError("Provide either non-empty expectation_text or intentions list.")
        return self


class ArtifactGapItem(BaseModel):
    """Single missing or incomplete field detected in `hero_origin.json` or `hero_ambition.json`."""

    artifact_name: Literal["hero_origin.json", "hero_ambition.json"]
    field_path: str = Field(..., min_length=1, max_length=256)
    prompt: str = Field(..., min_length=1, max_length=1000)


class ArtifactGapReport(BaseModel):
    """Structured response for `GET /api/artifacts/scan`."""

    status: Literal["success"] = "success"
    has_gaps: bool
    gaps: list[ArtifactGapItem] = Field(default_factory=list)
    results: str


class HistoricalJournalRecord(BaseModel):
    """Historical journal or expectation item with explicit `saga_status`."""

    type: Literal["journal", "expectation", "time_chunk"]
    date: str
    text: str
    correlation_id: str = ""
    updated_at: Optional[str] = None
    saga_status: SagaStatusType = "GRAPH_INJECTED"
    reflection: Optional[str] = None


class JiraJulesBridgeStatus(BaseModel):
    """Combined status payload for the Porter Hub Jira <-> Google Jules Command Center GUI."""

    status: Literal["success"] = "success"
    feature_id: str
    jira_configured: bool
    jules_cli_available: bool
    speckit_tasks: list[SpecKitTaskItem] = Field(default_factory=list)
    staged_jira_issues: list[JiraIssueRecord] = Field(default_factory=list)
    recent_work_orders: list[JulesWorkOrder] = Field(default_factory=list)
