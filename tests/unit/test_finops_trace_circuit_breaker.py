"""Unit & route tests for T108 FinOps observability traces & token-density circuit breaker."""

from types import SimpleNamespace
from unittest.mock import MagicMock
import jwt
import pytest

from src.app import app
from src.config import MongoConfig
from src.database.mongo_client.agent_health import AgentHeartbeatManager
from src.database.mongo_client.connection import MongoConnectionManager
from src.utils.monitoring import FirstServingMonitoringHandler
from src.utils.token_circuit_breaker import (
    TokenCircuitBreakerHandler,
    TokenLimitExceededError,
)


@pytest.fixture(autouse=True)
def _bind_mongomock(mock_mongo: MagicMock) -> None:
    """Bind MongoConnectionManager to an isolated mongomock client per test."""
    MongoConnectionManager._client = mock_mongo


def _fake_llm_result(
    tokens: int | None = None, *, meta_tokens: int | None = None, text: str = "ok"
):
    llm_output = {"token_usage": {"total_tokens": tokens}} if tokens is not None else {}
    msg = SimpleNamespace(usage_metadata={"total_tokens": meta_tokens}) if meta_tokens else None
    gen = SimpleNamespace(text=text, message=msg)
    return SimpleNamespace(llm_output=llm_output, generations=[[gen]])


def _auth_header(email: str = "hero@example.com", role: str = "user") -> dict[str, str]:
    token = jwt.encode(
        {"email": email, "role": role, "account_type": "hero"},
        "dummy_test_jwt_secret_key",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_sliding_window_token_density_and_window_expiry() -> None:
    """Token density cap trips within 60s burst and clears once the window advances."""
    now = [1000.0]
    breaker = TokenCircuitBreakerHandler(
        max_tokens=50000,
        max_tokens_per_minute=1000,
        max_requests_per_minute=10,
        user_email="alice@example.com",
        session_id="sess-density",
        clock_fn=lambda: now[0],
    )
    breaker.on_llm_start({}, ["p1"])
    breaker.on_llm_end(_fake_llm_result(tokens=600))
    assert breaker.snapshot()["window_tokens"] == 600

    # Advance 65s: window clears so another 600 tokens succeeds cleanly
    now[0] += 65.0
    breaker.on_llm_start({}, ["p2"])
    breaker.on_llm_end(_fake_llm_result(tokens=600))
    assert breaker.snapshot()["window_tokens"] == 600
    assert breaker.total_tokens_spent == 1200

    # Immediate 500-token burst pushes window to 1100 > 1000 -> trips!
    with pytest.raises(TokenLimitExceededError, match="Token-density limit exceeded"):
        breaker.on_llm_end(_fake_llm_result(tokens=500))
    assert breaker.tripped is True

    db = MongoConnectionManager.get_db()
    happenings = list(
        db[MongoConfig.FIRST_SERVING_HAPPENINGS_COLLECTION].find(
            {"user_email": "alice@example.com", "event": "circuit_breaker_tripped"}
        )
    )
    assert len(happenings) == 1


def test_request_rate_density_halts_fast_spin_loop_and_parses_usage_metadata() -> None:
    """Rapid low-token spin loop trips max_requests_per_minute and parses modern usage_metadata."""
    now = [500.0]
    breaker = TokenCircuitBreakerHandler(
        max_tokens=50000,
        max_tokens_per_minute=50000,
        max_requests_per_minute=2,
        user_email="loop@example.com",
        clock_fn=lambda: now[0],
    )
    breaker.on_llm_start({}, ["p1"])
    breaker.on_llm_end(_fake_llm_result(meta_tokens=42))
    breaker.on_llm_start({}, ["p2"])
    breaker.on_llm_end(_fake_llm_result(text="12345678"))  # fallback -> 2 tokens
    assert breaker.total_tokens_spent == 44

    with pytest.raises(TokenLimitExceededError, match="Request-density limit exceeded"):
        breaker.on_llm_start({}, ["p3"])

    breaker.reset()
    assert breaker.tripped is False
    assert breaker.total_tokens_spent == 0


def test_monitoring_tenant_isolation_provenance_and_finops_route() -> None:
    """Traces & happenings enforce tenant scoping, extract CID provenance, and serve API."""
    alice_mon = FirstServingMonitoringHandler(
        session_id="alice-s1", correlation_id="cid-alice", user_email="alice@example.com"
    )
    bob_mon = FirstServingMonitoringHandler(
        session_id="bob-s1", correlation_id="cid-bob", user_email="bob@example.com"
    )

    alice_mon.on_llm_start({}, ["hello"])
    alice_mon.on_llm_end(_fake_llm_result(tokens=150, text="reply"))
    alice_mon.on_tool_start({"name": "search_private_brain"}, "query")
    alice_mon.on_tool_end("Result [CID:evt-991]", name="search_private_brain")

    bob_mon.on_llm_end(_fake_llm_result(tokens=900, text="bob secret"))

    snap = AgentHeartbeatManager().get_observability_snapshot("alice@example.com")
    assert snap["recent_tokens_spent"] == 150
    assert snap["trace_count"] == 2
    assert snap["happening_count"] == 2
    prov = next(h["provenance"] for h in snap["happenings"] if "provenance" in h)
    assert "evt-991" in prov["extracted_correlation_ids"]

    client = app.test_client()
    assert client.get("/api/admin/finops_traces").status_code == 401
    resp = client.get("/api/admin/finops_traces", headers=_auth_header("alice@example.com"))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["recent_tokens_spent"] == 150
    assert all(t["user_email"] == "alice@example.com" for t in data["traces"])

    # Non-admin requesting bob's email via query param still only sees their own tenant data
    scoped = client.get(
        "/api/admin/finops_traces?user_email=bob@example.com",
        headers=_auth_header("alice@example.com", role="user"),
    )
    assert scoped.status_code == 200
    assert scoped.get_json()["user_email"] == "alice@example.com"
