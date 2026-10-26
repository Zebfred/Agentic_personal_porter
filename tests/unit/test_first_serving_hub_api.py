"""
Offline Unit & Contract Test Suite for First-Serving Agent API, Porter Hub Support
& Jira/Jules Bridge GUI (`003-first-serving-hub-api`).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import jwt
import pytest

from src.app import app
from src.config import MongoConfig
from src.database.mongo_client.connection import MongoConnectionManager
from src.database.mongo_storage import SovereignMongoStorage


@pytest.fixture(autouse=True)
def _bind_mongomock(mock_mongo: MagicMock) -> None:
    """Bind MongoConnectionManager to the isolated mongomock client for each test."""
    MongoConnectionManager._client = mock_mongo
    SovereignMongoStorage._indexes_ensured = False


def _auth_header(email: str = "hero@example.com") -> dict[str, str]:
    token = jwt.encode(
        {"email": email, "role": "user", "account_type": "hero"},
        "dummy_test_jwt_secret_key",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_us1_classification_queue_and_hub_metrics_delta() -> None:
    """Verify US1 staging queue, tenant isolation, and week-over-week detour delta."""
    client = app.test_client()
    storage = SovereignMongoStorage()
    storage.users_col.insert_one({"email": "hero@example.com", "username": "HeroOne"})

    resp_stage = client.post(
        "/api/calendar/classification_queue",
        headers=_auth_header("hero@example.com"),
        json={
            "source": "gcal_sync",
            "events": [
                {
                    "gcal_id": "evt-101",
                    "title": "Mystery Deep Work",
                    "start_time": "2026-10-25T09:00:00Z",
                },
                {
                    "gcal_id": "evt-102",
                    "title": "Ad-hoc Guild Sync",
                    "start_time": "2026-10-25T11:00:00Z",
                },
            ],
        },
    )
    assert resp_stage.status_code == 200
    assert resp_stage.get_json()["staged_count"] == 2

    client.post(
        "/api/calendar/classification_queue",
        headers=_auth_header("bob@example.com"),
        json={
            "events": [
                {
                    "gcal_id": "evt-bob-1",
                    "title": "Bob Private",
                    "start_time": "2026-10-25T12:00:00Z",
                }
            ]
        },
    )

    resp_queue = client.get(
        "/api/calendar/classification_queue", headers=_auth_header("hero@example.com")
    )
    assert resp_queue.status_code == 200
    q_data = resp_queue.get_json()
    assert q_data["count"] == 2
    assert all(r["user_email"] == "hero@example.com" for r in q_data["records"])

    now = datetime.now(timezone.utc)
    cur_iso = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_iso = (now - timedelta(days=9)).strftime("%Y-%m-%d")
    actual_col = storage.db[MongoConfig.ACTUAL_COLLECTION]
    for idx in range(4):
        actual_col.insert_one(
            {
                "_id": f"prev-det-{idx}",
                "user_id": "hero@example.com",
                "time_slot": {"start": prev_iso, "end": prev_iso},
                "actual": {"title": f"Old Distraction {idx}", "detour_type": "detrimental"},
            }
        )
    actual_col.insert_one(
        {
            "_id": "cur-det-1",
            "user_id": "hero@example.com",
            "time_slot": {"start": cur_iso, "end": cur_iso},
            "actual": {"title": "Recent Distraction", "detour_type": "detrimental"},
        }
    )
    actual_col.insert_one(
        {
            "_id": "cur-val-1",
            "user_id": "hero@example.com",
            "time_slot": {"start": cur_iso, "end": cur_iso},
            "actual": {"title": "Serendipitous Research", "detour_type": "valuable"},
        }
    )

    resp_metrics = client.get("/api/user/hub_metrics", headers=_auth_header("hero@example.com"))
    assert resp_metrics.status_code == 200
    m_data = resp_metrics.get_json()["data"]
    assert m_data["unclassified"] == 2
    assert m_data["valuable_detours"] == 1
    assert m_data["detrimental_detours"] == 5
    assert m_data["detrimental_improvement_pct"] == 75.0
    assert m_data["detrimental_delta"] == "↓ 75%"


def test_us4_jira_jules_bridge_status_endpoint() -> None:
    """Verify GET /api/integrations/jira/status returns Spec-Kit tasks and bridge flags."""
    client = app.test_client()
    resp = client.get(
        "/api/integrations/jira/status?feature_dir=specs/003-first-serving-hub-api",
        headers=_auth_header("hero@example.com"),
    )
    assert resp.status_code == 200
    payload = resp.get_json()["data"]
    assert payload["feature_id"] == "003-first-serving-hub-api"
    assert len(payload["speckit_tasks"]) >= 10
    assert any(t["task_id"] == "T001" for t in payload["speckit_tasks"])


def test_us2_artifact_scan_and_one_shot_weekly_planning() -> None:
    """Verify GET /api/artifacts/scan across origin+ambition and POST /api/planning batch."""
    client = app.test_client()
    storage = SovereignMongoStorage()
    storage.users_col.insert_one({"email": "planner@example.com", "username": "PlannerHero"})
    storage.save_hero_artifact(
        "hero_origin.json",
        {"origin_story": {"epochs": [{"name": "Academy Years", "experiences": []}]}},
        "PlannerHero",
    )
    storage.save_hero_artifact("hero_ambition.json", {"primary_quest": ""}, "PlannerHero")

    resp_scan = client.get("/api/artifacts/scan", headers=_auth_header("planner@example.com"))
    assert resp_scan.status_code == 200
    scan_data = resp_scan.get_json()
    assert scan_data["has_gaps"] is True
    artifacts_flagged = {g["artifact_name"] for g in scan_data["gaps"]}
    assert "hero_origin.json" in artifacts_flagged
    assert "hero_ambition.json" in artifacts_flagged

    resp_plan = client.post(
        "/api/planning",
        headers=_auth_header("planner@example.com"),
        json={
            "week_start_date": "2026-10-26",
            "expectation_summary": "Complete 003 Hub API and verify GUI",
            "intentions": [
                {
                    "title": "Build Hub Metrics Endpoint",
                    "pillar": "Career & Mastery",
                    "priority": "High",
                    "start_date": "2026-10-26",
                },
                {
                    "title": "Evening Mobility Session",
                    "pillar": "Health & Vitality",
                    "priority": "Medium",
                    "start_date": "2026-10-27",
                },
            ],
        },
    )
    assert resp_plan.status_code == 200
    assert resp_plan.get_json()["intentions_saved"] == 2

    resp_get_plan = client.get(
        "/api/planning?week_start_date=2026-10-26", headers=_auth_header("planner@example.com")
    )
    assert resp_get_plan.status_code == 200
    assert len(resp_get_plan.get_json()["data"]["intentions"]) == 2


def test_us3_historical_journal_review_returns_saga_status() -> None:
    """Verify GET /api/journal/history includes explicit saga_status and reflection."""
    client = app.test_client()
    storage = SovereignMongoStorage()
    storage.users_col.insert_one({"email": "scribe@example.com", "username": "ScribeHero"})
    storage.save_freeform_journal(
        date_str="2026-10-25",
        text="Completed the Jira-Jules bridge GUI integration.",
        user_id="ScribeHero",
        correlation_id="corr-scribe-1",
        saga_status="GRAPH_INJECTED",
        reflection="Strong alignment with architectural mastery.",
    )

    resp_hist = client.get(
        "/api/journal/history?limit=5", headers=_auth_header("scribe@example.com")
    )
    assert resp_hist.status_code == 200
    records = resp_hist.get_json()["data"]
    assert len(records) == 1
    assert records[0]["saga_status"] == "GRAPH_INJECTED"
    assert records[0]["reflection"] == "Strong alignment with architectural mastery."
