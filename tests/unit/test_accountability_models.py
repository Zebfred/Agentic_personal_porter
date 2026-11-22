"""Unit and adversarial boundary tests for North Star Accountability schemas."""

import pytest
from pydantic import ValidationError

from src.schemas.accountability_models import (
    AccountabilityDashboardResponse,
    GraceWindowRequest,
    NorthStarPillar,
    PillarStreakSummary,
    PillarUpsertBatchRequest,
    ReconCheckInRequest,
)


def test_valid_north_star_pillar_and_batch() -> None:
    """Valid career and restorative life pillars validate cleanly in a batch."""
    career = NorthStarPillar(
        pillar_id="cpp-airgap-drills",
        title="C++ Air-Gapped Fundamentals",
        category="career_fundamentals",
        weekly_target_count=4,
        target_unit="25m drills",
    )
    life = NorthStarPillar(
        pillar_id="protected-family-time",
        title="Protected Life & Relationship Time",
        category="life_relationship",
        weekly_target_count=3,
        target_unit="unplugged evenings",
        is_restorative_life_pillar=True,
    )
    batch = PillarUpsertBatchRequest(pillars=[career, life])
    assert len(batch.pillars) == 2
    assert batch.pillars[1].is_restorative_life_pillar is True


def test_batch_rejects_duplicate_ids_and_wip_overflow() -> None:
    """Batch enforces unique pillar_id values and hard cap of 6 pillars."""
    pillar = NorthStarPillar(
        pillar_id="joy-fuel-rl",
        title="LaUIrl & Swarm Defense",
        category="builder_joy_fuel",
    )
    with pytest.raises(ValidationError, match="Duplicate pillar_id"):
        PillarUpsertBatchRequest(pillars=[pillar, pillar])

    seven = [
        NorthStarPillar(
            pillar_id=f"pillar-{idx}",
            title=f"Pillar {idx}",
            category="career_fundamentals",
        )
        for idx in range(7)
    ]
    with pytest.raises(ValidationError):
        PillarUpsertBatchRequest(pillars=seven)


def test_adversarial_null_byte_and_slug_rejection() -> None:
    """Adversarial inputs containing null bytes or invalid slugs are rejected."""
    with pytest.raises(ValidationError):
        NorthStarPillar(
            pillar_id="Bad Slug!",
            title="Invalid",
            category="career_fundamentals",
        )
    with pytest.raises(ValidationError, match="Null bytes"):
        ReconCheckInRequest(
            pillar_id="cpp-airgap-drills",
            iso_date="2026-11-22",
            minutes_spent=25,
            win_note="clean\x00injected",
            idempotency_key="key-0001",
        )


def test_recon_entry_and_grace_window_validation() -> None:
    """Recon dates, duration bounds, and ISO-week grace windows enforce contracts."""
    entry = ReconCheckInRequest(
        pillar_id="cpp-airgap-drills",
        iso_date="2026-11-22",
        minutes_spent=25,
        win_note="Solved tree DP without AI lookup",
        idempotency_key="2026-11-22-cpp-01",
    )
    assert entry.source == "hub_recon"

    grace = GraceWindowRequest(iso_week="2026-W47", enabled=True, reason="Visiting parents")
    assert grace.iso_week == "2026-W47"

    with pytest.raises(ValidationError):
        GraceWindowRequest(iso_week="2026-W99", enabled=True)

    with pytest.raises(ValidationError):
        ReconCheckInRequest(
            pillar_id="cpp-airgap-drills",
            iso_date="11/22/2026",
            minutes_spent=25,
            idempotency_key="bad-date-01",
        )


def test_dashboard_response_and_markdown_export() -> None:
    """Dashboard response serializes streak summaries and renders portable Markdown."""
    summary = PillarStreakSummary(
        pillar_id="protected-family-time",
        title="Protected Life & Relationship Time",
        category="life_relationship",
        is_restorative_life_pillar=True,
        completed_this_week=3,
        weekly_target_count=3,
        completion_ratio=1.0,
        current_streak_weeks=4,
        longest_streak_weeks=4,
        streak_status="active",
    )
    resp = AccountabilityDashboardResponse(
        user_email="hero@example.com",
        iso_week="2026-W47",
        grace_mode_active=True,
        life_harmony_ratio=1.0,
        overall_completion_ratio=0.85,
        pillars=[summary],
    )
    payload = resp.model_dump()
    assert payload["grace_mode_active"] is True
    md = str(resp)
    assert "# North Star Accountability Snapshot (2026-W47)" in md
    assert "Protected Life & Relationship Time" in md
    assert "Restorative Life" in md
