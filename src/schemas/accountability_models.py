"""Pydantic v2 boundary schemas for North Star Accountability (004-north-star-accountability)."""

import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator

PillarCategory = Literal[
    "career_fundamentals",
    "business_finops",
    "builder_joy_fuel",
    "life_relationship",
    "health_energy",
]
StreakStatus = Literal["active", "at_risk", "paused_grace", "broken"]
CheckInSource = Literal["hub_recon", "calendar_sync", "cli_export", "mobile_quick"]

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_WEEK_RE = re.compile(r"^\d{4}-W(?:0[1-9]|[1-4]\d|5[0-3])$")


def _clean_text(value: str, *, allow_empty: bool = False) -> str:
    """Strip whitespace and reject null-byte injection across string boundaries."""
    if "\x00" in value:
        raise ValueError("Null bytes are not permitted in string fields.")
    cleaned = value.strip()
    if not allow_empty and not cleaned:
        raise ValueError("Field cannot be blank or whitespace-only.")
    return cleaned


class NorthStarPillar(BaseModel):
    """Tenant-scoped North Star pillar tracked in the 20-Second Recon Loop."""

    pillar_id: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=100)
    category: PillarCategory
    weekly_target_count: int = Field(default=3, ge=1, le=21)
    target_unit: str = Field(default="sessions", min_length=1, max_length=40)
    is_restorative_life_pillar: bool = False
    grace_eligible: bool = True
    active: bool = True

    @model_validator(mode="after")
    def validate_pillar(self) -> "NorthStarPillar":
        """Enforce slug format, non-blank strings, and safe defaults."""
        self.pillar_id = _clean_text(self.pillar_id)
        if not _SLUG_RE.match(self.pillar_id):
            raise ValueError("pillar_id must be a lowercase slug (a-z, 0-9, '-', '_').")
        self.title = _clean_text(self.title)
        self.target_unit = _clean_text(self.target_unit)
        _ = (
            self.weekly_target_count,
            self.is_restorative_life_pillar,
            self.grace_eligible,
            self.active,
        )
        return self


class PillarUpsertBatchRequest(BaseModel):
    """Batch upsert payload capped at 6 active pillars to prevent WIP overload."""

    pillars: list[NorthStarPillar] = Field(..., min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_unique_pillar_ids(self) -> "PillarUpsertBatchRequest":
        """Reject duplicate pillar_id values inside a single batch."""
        ids = [item.pillar_id for item in self.pillars]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate pillar_id values are not allowed in a batch.")
        return self


class ReconCheckInRequest(BaseModel):
    """20-Second Recon check-in payload logged against a North Star pillar."""

    pillar_id: str = Field(..., min_length=2, max_length=64)
    iso_date: str = Field(..., description="YYYY-MM-DD")
    minutes_spent: int = Field(..., ge=1, le=1440)
    win_note: str = Field(default="", max_length=500)
    idempotency_key: str = Field(..., min_length=4, max_length=128)
    source: CheckInSource = "hub_recon"

    @model_validator(mode="after")
    def validate_entry(self) -> "ReconCheckInRequest":
        """Validate slug, ISO date, duration bounds, and null-byte safety."""
        self.pillar_id = _clean_text(self.pillar_id)
        if not _SLUG_RE.match(self.pillar_id):
            raise ValueError("Invalid pillar_id format.")
        self.iso_date = _clean_text(self.iso_date)
        if not _ISO_DATE_RE.match(self.iso_date):
            raise ValueError("iso_date must match YYYY-MM-DD.")
        self.win_note = _clean_text(self.win_note, allow_empty=True)
        self.idempotency_key = _clean_text(self.idempotency_key)
        _ = (self.minutes_spent, self.source)
        return self


class GraceWindowRequest(BaseModel):
    """Toggle Vacation / Grace Mode for an ISO week without resetting career streaks."""

    iso_week: str = Field(..., description="YYYY-Www")
    enabled: bool = True
    reason: str = Field(default="Planned vacation or family time", max_length=200)

    @model_validator(mode="after")
    def validate_grace_window(self) -> "GraceWindowRequest":
        """Validate strict ISO week notation (YYYY-W01..YYYY-W53) and reason."""
        self.iso_week = _clean_text(self.iso_week)
        if not _ISO_WEEK_RE.match(self.iso_week):
            raise ValueError("iso_week must match YYYY-W01..YYYY-W53.")
        self.reason = _clean_text(self.reason, allow_empty=True)
        _ = self.enabled
        return self


class PillarStreakSummary(BaseModel):
    """Deterministic weekly streak readout for a single North Star pillar."""

    pillar_id: str
    title: str
    category: PillarCategory
    is_restorative_life_pillar: bool
    completed_this_week: int = Field(ge=0)
    weekly_target_count: int = Field(ge=1)
    completion_ratio: float = Field(ge=0.0, le=1.0)
    current_streak_weeks: int = Field(ge=0)
    longest_streak_weeks: int = Field(ge=0)
    streak_status: StreakStatus

    def __str__(self) -> str:
        """Render a concise single-line streak summary for logs and Markdown tables."""
        kind = "Restorative Life" if self.is_restorative_life_pillar else self.category
        pct = int(round(self.completion_ratio * 100))
        return (
            f"| {self.title} | {kind} | {self.completed_this_week}/{self.weekly_target_count}"
            f" ({pct}%) | {self.current_streak_weeks}w (best {self.longest_streak_weeks}w)"
            f" | `{self.streak_status}` |"
        )


class AccountabilityDashboardResponse(BaseModel):
    """Top-level tenant-scoped accountability response for Porter Hub & Markdown export."""

    status: Literal["success"] = "success"
    user_email: str = Field(..., min_length=3)
    iso_week: str
    grace_mode_active: bool = False
    life_harmony_ratio: float = Field(ge=0.0, le=1.0)
    overall_completion_ratio: float = Field(ge=0.0, le=1.0)
    pillars: list[PillarStreakSummary] = Field(default_factory=list)

    def __str__(self) -> str:
        """Render a portable, markdownlint-friendly status snapshot."""
        grace_label = "Active (Vacation/Grace)" if self.grace_mode_active else "Standard"
        lines = [
            f"# North Star Accountability Snapshot ({self.iso_week})",
            "",
            f"* **Mode**: {grace_label}",
            f"* **Overall Completion**: {int(round(self.overall_completion_ratio * 100))}%",
            f"* **Life Harmony Ratio**: {int(round(self.life_harmony_ratio * 100))}%",
            "",
            "| Pillar | Category | Weekly Progress | Streak | Status |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        lines.extend(str(p) for p in self.pillars)
        return "\n".join(lines) + "\n"
