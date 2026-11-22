"""Concurrent multi-tenant threading and hostile boundary stress tests (T109 + T110)."""

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import jwt
import pytest

from src.agents.audit_inspector import AuditInspector
from src.app import create_app
from src.config import MongoConfig
from src.database.mongo_client.connection import MongoConnectionManager
from src.utils.monitoring import FirstServingMonitoringHandler


@pytest.fixture(autouse=True)
def _bind_isolated_mongo(mock_mongo: MagicMock) -> None:
    """Bind MongoConnectionManager singleton to the per-test mongomock client."""
    MongoConnectionManager._client = mock_mongo


@pytest.fixture
def flask_app():
    """Return an isolated Flask app configured for testing."""
    application = create_app()
    application.config["TESTING"] = True
    return application


def _auth(email: str, username: str | None = None, role: str = "user") -> dict[str, str]:
    payload: dict[str, str] = {"email": email, "role": role, "account_type": "hero"}
    if username is not None:
        payload["username"] = username
    tok = jwt.encode(payload, "dummy_test_jwt_secret_key", algorithm="HS256")
    return {"Authorization": f"Bearer {tok}"}


def _run_tenant_pair(flask_app, idx: int) -> None:
    tenants = [
        ("alpha@example.com", "tenant_alpha", "beta@example.com", "tenant_beta"),
        ("beta@example.com", "tenant_beta", "alpha@example.com", "tenant_alpha"),
    ]
    email, user, other_email, spoof = tenants[idx % 2]
    client = flask_app.test_client()
    hdrs = _auth(email, username=user)
    body = {
        "journal_entry": f"note-{user}-{idx}",
        "log_data": {"day": "2026-07-14"},
        "username": spoof,
        "user_id": spoof,
    }
    jr = client.post("/process_journal", json=body, headers=hdrs)
    assert jr.status_code == 200
    jb = jr.get_json()
    assert jb["username"] == user and spoof not in jb["result"]
    assert jb["result"] == f"reflection:{user}:note-{user}-{idx}"

    cr = client.get("/get_calendar_events?date=2026-07-14", headers=hdrs)
    assert cr.status_code == 200
    cb = cr.get_json()
    assert cb["username"] == user and other_email not in cb["events"][0]["title"]
    assert cb["events"][0]["title"] == f"Meeting for {email}"


def test_concurrent_multitenant_process_journal_and_calendar_isolation(flask_app) -> None:
    """Concurrent requests across tenant_alpha and tenant_beta have zero cross-tenant leakage."""
    db = MongoConnectionManager.get_db()
    db["users"].insert_many(
        [
            {"email": "alpha@example.com", "username": "tenant_alpha"},
            {"email": "beta@example.com", "username": "tenant_beta"},
        ]
    )

    def _refl(entry: str, _log: dict, username: str = "Hero") -> str:
        return f"reflection:{username}:{entry}"

    def _cal(date_str: str, email: str | None = None) -> list[dict]:
        slot = {"dateTime": f"{date_str}T09:00:00Z"}
        return [{"id": f"e-{email}", "summary": f"Meeting for {email}", "start": slot, "end": slot}]

    with (
        patch("src.routes.journal_routes.run_porter_reflection", side_effect=_refl),
        patch("src.routes.journal_routes.fetch_calendar_events_for_date", return_value=[]),
        patch("src.routes.calendar_routes.fetch_calendar_events_for_date", side_effect=_cal),
        ThreadPoolExecutor(max_workers=8) as pool,
    ):
        list(pool.map(lambda i: _run_tenant_pair(flask_app, i), range(16)))

    a_docs = list(db["agent_reflections"].find({"user_id": "tenant_alpha"}))
    b_docs = list(db["agent_reflections"].find({"user_id": "tenant_beta"}))
    assert len(a_docs) == 8 and len(b_docs) == 8
    assert all(d["user_email"] == "alpha@example.com" for d in a_docs)
    assert all(d["user_email"] == "beta@example.com" for d in b_docs)


@pytest.mark.parametrize(
    "raw_body",
    [
        "{malformed-json",
        '["not", "a", "dict"]',
        '{"journal_entry": "bad\\u0000byte", "log_data": {"day": "2026-07-14"}}',
        '{"journal_entry": 12345, "log_data": "wrong-type"}',
        '{"journal_entry": "' + ("A" * 16000) + '", "log_data": {"day": "2026-07-14"}}',
        '{"journal_entry": "ok", "log_data": {"day": "' + ("D" * 100) + '"}}',
        '{"journal_entry": {"$ne": ""}, "log_data": {"day": "2026-07-14"}}',
    ],
)
def test_hostile_boundary_inputs_process_journal_no_500(flask_app, raw_body: str) -> None:
    """Hostile payloads to /process_journal return clean 400 responses with zero 500s."""
    hdrs = {**_auth("guard@example.com", "guard_hero"), "Content-Type": "application/json"}
    resp = flask_app.test_client().post("/process_journal", data=raw_body, headers=hdrs)
    assert resp.status_code == 400 and "error" in (resp.get_json() or {})


@pytest.mark.parametrize(
    "bad_date",
    ["2026-07-01%00", "'; DROP TABLE events; --", "2026-13-45", "A" * 2048, "٢٠٢٦-٠٧-١٤"],
)
def test_hostile_boundary_inputs_calendar_and_auth_no_500(flask_app, bad_date: str) -> None:
    """Hostile calendar query dates and missing auth return clean 4xx without 500s."""
    client = flask_app.test_client()
    assert client.post("/process_journal", json={"journal_entry": "x"}).status_code == 401
    assert client.get("/get_calendar_events?date=2026-07-14").status_code == 401
    resp = client.get(f"/get_calendar_events?date={bad_date}", headers=_auth("c@example.com", "c"))
    assert resp.status_code == 400 and "error" in (resp.get_json() or {})


def test_audit_inspector_tenant_username_threading() -> None:
    """AuditInspector scopes pending/approved records and heartbeat logs to tenant username."""
    db = MongoConnectionManager.get_db()
    base = {
        "duration_minutes": 45,
        "start": "2026-07-14T09:00:00Z",
        "status": "Pending Verification",
    }
    a_doc = {**base, "gcal_id": "a1", "title": "Build", "pillar": "Wealth", "confidence_score": 40}
    b_doc = {**base, "gcal_id": "b1", "title": "Secret", "pillar": "Health", "confidence_score": 20}
    db[MongoConfig.DAILY_CATEGORIZED_EVENTS].insert_many(
        [{**a_doc, "user_email": "alpha@example.com"}, {**b_doc, "user_email": "beta@example.com"}]
    )
    insp = AuditInspector()
    pend = insp.batch_unverified_records("alpha@example.com", username="tenant_alpha")
    assert [r["gcal_id"] for r in pend] == ["a1"] and pend[0]["username"] == "tenant_alpha"
    assert insp.approve_batch(["a1", "b1"], "alpha@example.com", username="tenant_alpha") == 1
    assert (
        db[MongoConfig.ACTUAL_COLLECTION].find_one({"gcal_id": "a1"})["username"] == "tenant_alpha"
    )
    assert db[MongoConfig.ACTUAL_COLLECTION].find_one({"gcal_id": "b1"}) is None
    ver = insp.get_recently_verified_records("alpha@example.com", username="tenant_alpha")
    assert [r["gcal_id"] for r in ver] == ["a1"]
    runs = list(db[MongoConfig.AGENT_HEALTH_COLLECTION].find({"agent_name": "audit_inspector"}))
    assert runs and all(r["username"] == "tenant_alpha" for r in runs)


def test_chat_and_finops_routes_thread_username_and_reject_spoofing(flask_app) -> None:
    """Chat and FinOps trace routes ignore spoofed fields and reject NUL bytes."""
    mon = FirstServingMonitoringHandler(
        "s-a", user_email="alpha@example.com", username="tenant_alpha"
    )
    mon.on_llm_start({}, ["hello"])
    client = flask_app.test_client()
    hdrs = _auth("alpha@example.com", username="tenant_alpha")

    tr = client.get("/api/admin/finops_traces?user_email=beta@example.com", headers=hdrs)
    assert tr.status_code == 200 and tr.get_json()["username"] == "tenant_alpha"
    assert tr.get_json()["traces"][0]["username"] == "tenant_alpha"

    with patch("src.routes.chat_routes.run_first_serving_porter") as mock_p:
        mock_p.return_value = {"response": "ok", "transparency_logs": []}
        res = client.post(
            "/api/chat/porter", json={"message": "hi", "username": "beta"}, headers=hdrs
        )
        assert res.status_code == 200
        mock_p.assert_called_once_with(
            "hi", username="tenant_alpha", user_email="alpha@example.com"
        )
        bad = client.post("/api/chat/porter", json={"message": "null\x00byte"}, headers=hdrs)
        assert bad.status_code == 400
