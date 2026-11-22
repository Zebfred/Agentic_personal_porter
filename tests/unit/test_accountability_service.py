"""Unit tests for North Star Accountability storage & deterministic streak engine (004)."""

from unittest.mock import MagicMock
import pytest

from src.config import MongoConfig
from src.database.mongo_client.connection import MongoConnectionManager
from src.schemas.accountability_models import (
    GraceWindowRequest,
    NorthStarPillar,
    ReconCheckInRequest,
)
from src.services.accountability_service import (
    build_accountability_dashboard,
    get_pillars_payload,
    log_recon_entry,
    save_pillars_batch,
    set_grace_window,
)


@pytest.fixture()
def db(mock_mongo: MagicMock) -> MagicMock:
    """Provide an isolated mongomock database bound to MongoConnectionManager."""
    MongoConnectionManager._client = mock_mongo
    return mock_mongo[MongoConfig.DB_NAME]


def _seed_two_pillars(db: MagicMock, email: str) -> None:
    pillars = [
        NorthStarPillar(
            pillar_id="cpp-airgap-drills",
            title="C++ Air-Gapped Fundamentals",
            category="career_fundamentals",
            weekly_target_count=2,
            target_unit="25m drills",
            is_restorative_life_pillar=False,
            grace_eligible=True,
        ),
        NorthStarPillar(
            pillar_id="protected-family-time",
            title="Protected Life & Relationship Time",
            category="life_relationship",
            weekly_target_count=2,
            target_unit="unplugged evenings",
            is_restorative_life_pillar=True,
            grace_eligible=True,
        ),
    ]
    res = save_pillars_batch(db, email, pillars)
    assert res["saved_count"] == 2


def test_new_tenant_gets_starter_templates_and_zeroed_dashboard(db: MagicMock) -> None:
    """New tenant receives starter templates and zeroed metrics with no errors."""
    payload = get_pillars_payload(db, "new@example.com")
    assert payload["pillars"] == []
    assert len(payload["starter_templates"]) == 4

    dash = build_accountability_dashboard(db, "new@example.com", iso_week="2026-W47")
    assert dash.overall_completion_ratio == 0.0
    assert dash.life_harmony_ratio == 0.0
    assert dash.pillars == []


def test_multi_week_streak_grace_freeze_and_restorative_life_wins(db: MagicMock) -> None:
    """Grace week freezes career streak without reset while restorative life wins count."""
    email = "hero@example.com"
    _seed_two_pillars(db, email)

    # Week 2026-W46 (Mon 2026-11-09): hit target of 2 C++ drills
    for idx, day in enumerate(("2026-11-09", "2026-11-11"), 1):
        body, code = log_recon_entry(
            db,
            email,
            ReconCheckInRequest(
                pillar_id="cpp-airgap-drills",
                iso_date=day,
                minutes_spent=25,
                win_note=f"Air-gapped drill {idx}",
                idempotency_key=f"w46-cpp-{idx}",
            ),
        )
        assert code == 201
        assert body["created"] is True

    # Enable Vacation/Grace Mode for 2026-W47 (Mon 2026-11-16..Sun 2026-11-22)
    set_grace_window(
        db,
        email,
        GraceWindowRequest(iso_week="2026-W47", enabled=True, reason="Visiting parents"),
    )

    # Log 2 restorative family wins during 2026-W47
    for idx, day in enumerate(("2026-11-21", "2026-11-22"), 1):
        _, code = log_recon_entry(
            db,
            email,
            ReconCheckInRequest(
                pillar_id="protected-family-time",
                iso_date=day,
                minutes_spent=90,
                win_note="Unplugged family dinner",
                idempotency_key=f"w47-fam-{idx}",
            ),
        )
        assert code == 201

    dash = build_accountability_dashboard(db, email, iso_week="2026-W47")
    assert dash.grace_mode_active is True
    assert dash.life_harmony_ratio == 1.0

    by_id = {p.pillar_id: p for p in dash.pillars}
    assert by_id["cpp-airgap-drills"].streak_status == "paused_grace"
    assert by_id["cpp-airgap-drills"].current_streak_weeks == 1
    assert by_id["protected-family-time"].streak_status == "active"
    assert by_id["protected-family-time"].current_streak_weeks == 1


def test_idempotency_dedup_and_strict_tenant_isolation(db: MagicMock) -> None:
    """Duplicate idempotency_key deduplicates and tenants never see each other's data."""
    _seed_two_pillars(db, "alice@example.com")
    _seed_two_pillars(db, "bob@example.com")

    req = ReconCheckInRequest(
        pillar_id="cpp-airgap-drills",
        iso_date="2026-11-22",
        minutes_spent=25,
        win_note="Solved graph BFS",
        idempotency_key="dup-key-01",
    )
    first_body, first_code = log_recon_entry(db, "alice@example.com", req)
    second_body, second_code = log_recon_entry(db, "alice@example.com", req)
    assert first_code == 201
    assert first_body["created"] is True
    assert second_code == 200
    assert second_body["created"] is False

    bob_dash = build_accountability_dashboard(db, "bob@example.com", iso_week="2026-W47")
    bob_cpp = next(p for p in bob_dash.pillars if p.pillar_id == "cpp-airgap-drills")
    assert bob_cpp.completed_this_week == 0

    alice_dash = build_accountability_dashboard(db, "alice@example.com", iso_week="2026-W47")
    alice_cpp = next(p for p in alice_dash.pillars if p.pillar_id == "cpp-airgap-drills")
    assert alice_cpp.completed_this_week == 1
