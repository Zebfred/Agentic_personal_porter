"""Offline Flask Blueprint tests for /api/accountability/* endpoints (004)."""

from unittest.mock import MagicMock
import jwt
import pytest

from src.app import app
from src.database.mongo_client.connection import MongoConnectionManager
from src.database.mongo_storage import SovereignMongoStorage


@pytest.fixture(autouse=True)
def _bind_mongomock(mock_mongo: MagicMock) -> None:
    """Isolate every route test on a clean mongomock instance."""
    MongoConnectionManager._client = mock_mongo
    SovereignMongoStorage._indexes_ensured = False


def _auth_header(email: str = "hero@example.com") -> dict[str, str]:
    token = jwt.encode(
        {"email": email, "role": "user", "account_type": "hero"},
        "dummy_test_jwt_secret_key",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_accountability_endpoints_require_auth() -> None:
    """Unauthenticated requests to /api/accountability/* are rejected with 401."""
    client = app.test_client()
    assert client.get("/api/accountability/pillars").status_code == 401
    assert client.get("/api/accountability/streaks").status_code == 401
    assert client.get("/api/accountability/export-markdown").status_code == 401


def test_accountability_end_to_end_flow_and_markdown_export() -> None:
    """Exercise PUT pillars, POST recon win, POST grace-window, GET streaks, and Markdown."""
    client = app.test_client()
    headers = _auth_header("hero@example.com")

    put_resp = client.put(
        "/api/accountability/pillars",
        headers=headers,
        json={
            "pillars": [
                {
                    "pillar_id": "cpp-airgap-drills",
                    "title": "C++ Air-Gapped Fundamentals",
                    "category": "career_fundamentals",
                    "weekly_target_count": 2,
                    "target_unit": "25m drills",
                },
                {
                    "pillar_id": "protected-family-time",
                    "title": "Protected Life & Relationship Time",
                    "category": "life_relationship",
                    "weekly_target_count": 1,
                    "target_unit": "evenings",
                    "is_restorative_life_pillar": True,
                },
            ]
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.get_json()["saved_count"] == 2

    log_resp = client.post(
        "/api/accountability/recon-checkin",
        headers=headers,
        json={
            "pillar_id": "protected-family-time",
            "iso_date": "2026-11-22",
            "minutes_spent": 90,
            "win_note": "Family dinner before trip",
            "idempotency_key": "route-win-001",
        },
    )
    assert log_resp.status_code == 201
    assert log_resp.get_json()["pillar_streak"]["streak_status"] == "active"

    grace_resp = client.post(
        "/api/accountability/grace-window",
        headers=headers,
        json={"iso_week": "2026-W47", "enabled": True, "reason": "Vacation"},
    )
    assert grace_resp.status_code == 200

    streaks_resp = client.get("/api/accountability/streaks?iso_week=2026-W47", headers=headers)
    assert streaks_resp.status_code == 200
    body = streaks_resp.get_json()
    assert body["grace_mode_active"] is True
    assert body["life_harmony_ratio"] == 1.0

    md_resp = client.get("/api/accountability/export-markdown?iso_week=2026-W47", headers=headers)
    assert md_resp.status_code == 200
    md_text = md_resp.get_data(as_text=True)
    assert "# North Star Accountability Snapshot (2026-W47)" in md_text
    assert "Protected Life & Relationship Time" in md_text


def test_accountability_route_validation_and_tenant_isolation() -> None:
    """Reject malformed ISO week/payloads with 422 and isolate cross-tenant data."""
    client = app.test_client()
    alice = _auth_header("alice@example.com")
    bob = _auth_header("bob@example.com")

    bad_week = client.get("/api/accountability/streaks?iso_week=2026-W99", headers=alice)
    assert bad_week.status_code == 422

    bad_payload = client.put(
        "/api/accountability/pillars",
        headers=alice,
        json={"pillars": [{"pillar_id": "BAD!", "title": "x", "category": "career_fundamentals"}]},
    )
    assert bad_payload.status_code == 422

    client.put(
        "/api/accountability/pillars",
        headers=alice,
        json={
            "pillars": [
                {
                    "pillar_id": "alice-only",
                    "title": "Alice Private Goal",
                    "category": "career_fundamentals",
                }
            ]
        },
    )
    bob_pillars = client.get("/api/accountability/pillars", headers=bob).get_json()
    assert bob_pillars["pillars"] == []


def test_hub_html_includes_accessible_accountability_widget() -> None:
    """Verify Porter Hub HTML renders the accessible North Star widget using semantic CSS tokens."""
    from pathlib import Path

    html = Path("frontend/index.html").read_text(encoding="utf-8")
    for marker in (
        'id="north-star-accountability-section"',
        'id="btn-acct-grace-toggle"',
        'id="btn-acct-export-md"',
        'id="acct-pillars-grid"',
        'aria-live="polite"',
        "var(--primary-action)",
        "var(--status-success)",
    ):
        assert marker in html
