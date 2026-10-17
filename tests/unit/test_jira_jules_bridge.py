"""
Offline Unit & Contract Test Suite for Unified Spec-Kit, Jira, and Jules Bridge (002-jira-jules-bridge).

Covers:
- US1 (T007): Bi-directional JiraClient read/write, URL validation, batched JiraStorage, pending_upstream fallback, Neo4j Quest merge, and /api/integrations/jira/sync
- US2 (T011): Spec-Kit tasks.md parsing (\bT\d{3,}\b), persona domain mapping, idempotent deduplication, and /api/integrations/jira/speckit-push
- US3 (T014): JulesDispatcher work order assembly, .jules/<persona>.md playbook injection, shell=False subprocess safety, Jira session annotation, and /api/integrations/jules/dispatch
"""
from pathlib import Path
from unittest.mock import MagicMock, patch
import jwt
import pytest
from pydantic import ValidationError

from src.database.mongo_client.uuid_manager import UUIDGenerator
from src.database.mongo_client.jira_storage import JiraStorage
from src.schemas.jira_models import (
    JiraIssueRecord,
    JulesWorkOrder,
    SpecKitTaskItem,
)
from src.integrations.jira_client import JiraClient, JiraClientError
from src.integrations.jules_dispatcher import JulesDispatcher, JulesDispatchError
from src.orchestrators.speckit_jira_bridge import (
    parse_speckit_tasks_markdown,
    sync_feature_to_jira,
)


from src.database.mongo_client.connection import MongoConnectionManager
import src.routes.jira_routes as jira_routes_module


@pytest.fixture(autouse=True)
def _isolate_jira_mongo(mock_mongo: MagicMock) -> None:
    """Ensure each test receives a fresh, isolated mongomock client."""
    MongoConnectionManager._client = mock_mongo
    jira_routes_module._jira_storage = None


# ---------------------------------------------------------------------------
# Phase 1 & 2 Foundational Contract Tests (UUIDs, Schemas, Batched Storage)
# ---------------------------------------------------------------------------

def test_uuid_generator_jira_deterministic_and_tenant_isolated() -> None:
    """Verify composite UUIDv5 generation is deterministic and isolated by user_email."""
    u1_a = UUIDGenerator.generate_for_jira_issue("PORTER-101", "alice@example.com")
    u1_b = UUIDGenerator.generate_for_jira_issue("PORTER-101", "alice@example.com")
    u2 = UUIDGenerator.generate_for_jira_issue("PORTER-101", "bob@example.com")

    assert u1_a == u1_b
    assert u1_a != u2


def test_pydantic_models_reject_invalid_patterns_and_null_bytes() -> None:
    """Verify strict regex and null-byte defenses (Crii / Sentinel)."""
    with pytest.raises(ValidationError):
        SpecKitTaskItem(
            task_id="INVALID-1",
            feature_id="002-jira-jules-bridge",
            title="Invalid task ID format",
        )

    with pytest.raises(ValidationError):
        JiraIssueRecord(
            uuid=UUIDGenerator.generate_for_jira_issue("PORTER-1", "hero@example.com"),
            user_email="hero@example.com",
            jira_key="PORTER-1",
            project_key="PORTER",
            summary="Bad\x00Summary",
            correlation_id="corr-123",
        )


def test_jira_storage_bulk_upsert_and_projected_dedup(mock_mongo: MagicMock) -> None:
    """Verify Bolt-compliant bulk_write and projected task_id deduplication."""
    storage = JiraStorage()
    rec1 = JiraIssueRecord(
        uuid=UUIDGenerator.generate_for_jira_issue("PORTER-1", "hero@example.com"),
        user_email="hero@example.com",
        jira_key="PORTER-1",
        project_key="PORTER",
        task_id="T001",
        feature_id="002-jira-jules-bridge",
        summary="T001: Configure constants",
        persona="bolt",
        correlation_id="corr-t001",
    )
    rec2 = JiraIssueRecord(
        uuid=UUIDGenerator.generate_for_jira_issue("LOCAL-T002", "hero@example.com"),
        user_email="hero@example.com",
        jira_key="LOCAL-T002",
        project_key="PORTER",
        task_id="T002",
        feature_id="002-jira-jules-bridge",
        summary="T002: Offline queued issue",
        sync_status="pending_upstream",
        correlation_id="corr-t002",
    )

    counts = storage.bulk_upsert_issues([rec1, rec2])
    assert counts["upserted_count"] == 2

    mappings = storage.get_existing_task_mappings("hero@example.com", "PORTER")
    assert "T001" in mappings
    assert mappings["T001"]["jira_key"] == "PORTER-1"
    assert "_id" not in mappings["T001"]

    pending = storage.get_pending_upstream_issues("hero@example.com", "PORTER")
    assert len(pending) == 1
    assert pending[0].jira_key == "LOCAL-T002"


# ---------------------------------------------------------------------------
# User Story 1 Tests (T007): Bi-Directional Jira Client & Sync
# ---------------------------------------------------------------------------

def test_us1_jira_client_validates_credentials_and_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure JiraClient fails fast on missing credentials or insecure URLs (Sentinel)."""
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)

    with pytest.raises(JiraClientError, match="Missing required Jira configuration"):
        JiraClient.from_env()

    with pytest.raises(JiraClientError, match="Invalid JIRA_BASE_URL"):
        JiraClient(
            base_url="not-a-valid-url",
            email="hero@example.com",
            api_token="secret-token",
            project_key="PORTER",
        )


def test_us1_jira_client_read_and_write_operations() -> None:
    """Verify JiraClient fetch_issues, create_issue, transition_issue, and add_comment."""
    client = JiraClient(
        base_url="https://nexus.atlassian.net",
        email="hero@example.com",
        api_token="token-xyz",
        project_key="PORTER",
    )

    with patch.object(client.session, "request") as mock_req:
        # 1. Fetch issues via JQL
        mock_resp_search = MagicMock()
        mock_resp_search.status_code = 200
        mock_resp_search.json.return_value = {
            "issues": [
                {
                    "key": "PORTER-10",
                    "fields": {
                        "summary": "T001: Setup config in src/config.py",
                        "status": {"name": "In Progress"},
                        "issuetype": {"name": "Task"},
                        "labels": ["speckit", "jules:bolt"],
                        "description": None,
                    },
                }
            ]
        }
        mock_req.return_value = mock_resp_search

        issues = client.fetch_issues(
            user_email="hero@example.com",
            project_key="PORTER",
            correlation_id="corr-sync-1",
        )
        assert len(issues) == 1
        assert issues[0].jira_key == "PORTER-10"
        assert issues[0].task_id == "T001"
        assert issues[0].persona == "bolt"

        # 2. Create issue
        mock_resp_create = MagicMock()
        mock_resp_create.status_code = 201
        mock_resp_create.json.return_value = {"key": "PORTER-11"}
        mock_req.return_value = mock_resp_create

        created_key = client.create_issue(
            summary="T002: Extend UUIDGenerator",
            description="Detailed task spec",
            issue_type="Task",
            labels=["speckit", "jules:sentinel"],
        )
        assert created_key == "PORTER-11"

        # 3. Transition issue
        mock_resp_trans_get = MagicMock()
        mock_resp_trans_get.status_code = 200
        mock_resp_trans_get.json.return_value = {
            "transitions": [{"id": "31", "name": "Done"}]
        }
        mock_resp_trans_post = MagicMock()
        mock_resp_trans_post.status_code = 204
        mock_req.side_effect = [mock_resp_trans_get, mock_resp_trans_post]

        assert client.transition_issue("PORTER-11", "Done") is True

        # 4. Add comment
        mock_req.side_effect = None
        mock_resp_comment = MagicMock()
        mock_resp_comment.status_code = 201
        mock_resp_comment.json.return_value = {"id": "999"}
        mock_req.return_value = mock_resp_comment

        assert client.add_comment("PORTER-11", "Dispatched to Jules session jules-123") is True


def test_us1_jira_sync_endpoint_and_neo4j_merge(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify POST /api/integrations/jira/sync pulls issues and merges to MongoDB + Neo4j."""
    from src.app import app

    monkeypatch.setenv("JIRA_BASE_URL", "https://nexus.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "hero@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "secret-token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "PORTER")

    token = jwt.encode(
        {"email": "hero@example.com", "role": "user", "account_type": "hero"},
        "dummy_test_jwt_secret_key",
        algorithm="HS256",
    )

    sample_record = JiraIssueRecord(
        uuid=UUIDGenerator.generate_for_jira_issue("PORTER-77", "hero@example.com"),
        user_email="hero@example.com",
        jira_key="PORTER-77",
        project_key="PORTER",
        task_id="T001",
        summary="T001: Sample issue",
        status="To Do",
        persona="bolt",
        correlation_id="corr-77",
    )

    with patch("src.routes.jira_routes.JiraClient.from_env") as mock_from_env:
        mock_client = MagicMock()
        mock_client.project_key = "PORTER"
        mock_client.fetch_issues.return_value = [sample_record]
        mock_from_env.return_value = mock_client

        test_client = app.test_client()
        resp = test_client.post(
            "/api/integrations/jira/sync",
            json={"project_key": "PORTER", "max_results": 25},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["pulled_count"] == 1
        assert data["upserted_count"] == 1


# ---------------------------------------------------------------------------
# User Story 2 Tests (T011): Spec-Kit tasks.md Parsing & Jira Deduplication
# ---------------------------------------------------------------------------

def test_us2_parse_speckit_tasks_and_infer_personas(tmp_path: Path) -> None:
    """Verify tasks.md regex parsing (\bT\d{3,}\b) and persona domain inference."""
    sample_tasks = """# Tasks: Sample Feature
- [ ] T001 Add constants in `src/config.py`
- [ ] T002 [P] [US1] Harden auth check in `src/routes/auth_middleware.py`
- [x] T003 [P] [US2] Optimize bulk_write query in `src/database/mongo_client/jira_storage.py`
- [ ] T1000 [US3] Update UI accessibility labels in `frontend/index.html`
"""
    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text(sample_tasks, encoding="utf-8")

    parsed = parse_speckit_tasks_markdown(tasks_file, feature_id="002-jira-jules-bridge")
    assert len(parsed) == 4

    assert parsed[0].task_id == "T001"
    assert parsed[0].is_parallel is False
    assert parsed[0].completed is False

    assert parsed[1].task_id == "T002"
    assert parsed[1].is_parallel is True
    assert parsed[1].user_story == "US1"
    assert parsed[1].persona == "sentinel"

    assert parsed[2].task_id == "T003"
    assert parsed[2].completed is True
    assert parsed[2].persona == "bolt"

    assert parsed[3].task_id == "T1000"
    assert parsed[3].persona == "palette"


def test_us2_sync_feature_to_jira_deduplicates_existing_tasks(tmp_path: Path) -> None:
    """Ensure repeated Spec-Kit-to-Jira sync runs skip already-mapped T001+ tasks (SC-002)."""
    feature_dir = tmp_path / "002-jira-jules-bridge"
    feature_dir.mkdir()
    (feature_dir / "spec.md").write_text("# Feature Specification: Test Bridge\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [ ] T001 First task in `src/config.py`\n"
        "- [ ] T002 [P] [US1] Second task in `src/database/mongo_client/jira_storage.py`\n",
        encoding="utf-8",
    )

    storage = JiraStorage()
    # Pre-seed T001 as already synced in MongoDB
    existing = JiraIssueRecord(
        uuid=UUIDGenerator.generate_for_jira_issue("PORTER-50", "hero@example.com"),
        user_email="hero@example.com",
        jira_key="PORTER-50",
        project_key="PORTER",
        task_id="T001",
        feature_id="002-jira-jules-bridge",
        summary="T001: First task in src/config.py",
        correlation_id="corr-existing",
    )
    storage.bulk_upsert_issues([existing])

    result = sync_feature_to_jira(
        feature_dir=feature_dir,
        user_email="hero@example.com",
        project_key="PORTER",
        dry_run=True,
        storage=storage,
    )

    assert result["dry_run"] is True
    assert "T001" in result["skipped_tasks"]
    assert len(result["created_tasks"]) == 1
    assert result["created_tasks"][0]["task_id"] == "T002"
    assert result["created_tasks"][0]["persona"] == "bolt"


# ---------------------------------------------------------------------------
# User Story 3 Tests (T014): Jules Work Order Formatter & Dispatcher
# ---------------------------------------------------------------------------

def test_us3_jules_dispatcher_builds_work_order_with_playbook_and_gates() -> None:
    """Verify JulesDispatcher injects .jules/<persona>.md rules and verification commands (SC-003)."""
    dispatcher = JulesDispatcher()
    issue = JiraIssueRecord(
        uuid=UUIDGenerator.generate_for_jira_issue("PORTER-88", "hero@example.com"),
        user_email="hero@example.com",
        jira_key="PORTER-88",
        project_key="PORTER",
        task_id="T006",
        feature_id="002-jira-jules-bridge",
        summary="T006: Implement JiraStorage bulk_write in src/database/mongo_client/jira_storage.py",
        description="Must enforce explicit query projections and batched bulk_write.",
        persona="bolt",
        correlation_id="corr-88",
    )

    work_order = dispatcher.build_work_order(
        issue=issue,
        target_paths=["src/database/mongo_client/jira_storage.py"],
        dry_run=True,
    )

    assert isinstance(work_order, JulesWorkOrder)
    assert work_order.persona == "bolt"
    assert work_order.playbook_path == ".jules/bolt.md"
    assert "make test-bolt" in work_order.verification_commands
    assert "make verify-done" in work_order.verification_commands
    assert "PORTER-88" in work_order.formatted_prompt
    assert "T006" in work_order.formatted_prompt
    assert "Bolt's Journal" in work_order.formatted_prompt


def test_us3_jules_dispatcher_executes_cli_with_shell_false_and_annotates_jira() -> None:
    """Verify live dispatch uses shell=False and records session ID back to Jira."""
    dispatcher = JulesDispatcher()
    issue = JiraIssueRecord(
        uuid=UUIDGenerator.generate_for_jira_issue("PORTER-89", "hero@example.com"),
        user_email="hero@example.com",
        jira_key="PORTER-89",
        project_key="PORTER",
        task_id="T008",
        feature_id="002-jira-jules-bridge",
        summary="T008: Implement JiraClient in src/integrations/jira_client.py",
        description="Zero-trust Jira client implementation.",
        persona="sentinel",
        correlation_id="corr-89",
    )

    work_order = dispatcher.build_work_order(
        issue=issue,
        target_paths=["src/integrations/jira_client.py"],
        dry_run=False,
    )

    mock_jira = MagicMock()
    mock_jira.add_comment.return_value = True

    with patch("src.integrations.jules_dispatcher.subprocess.run") as mock_subproc:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Session created: jules-session-4242\n"
        mock_proc.stderr = ""
        mock_subproc.return_value = mock_proc

        updated_order = dispatcher.dispatch_work_order(
            work_order=work_order,
            jira_client=mock_jira,
        )

        assert updated_order.dispatch_status == "dispatched"
        assert updated_order.jules_session_id == "jules-session-4242"
        # Verify shell=False security invariant (Sentinel)
        _, kwargs = mock_subproc.call_args
        assert kwargs.get("shell") is False
        mock_jira.add_comment.assert_called_once()


def test_us3_jules_dispatcher_blocks_incomplete_issue() -> None:
    """Ensure pre-dispatch validation blocks tickets missing specification context."""
    dispatcher = JulesDispatcher()
    incomplete_issue = JiraIssueRecord(
        uuid=UUIDGenerator.generate_for_jira_issue("PORTER-90", "hero@example.com"),
        user_email="hero@example.com",
        jira_key="PORTER-90",
        project_key="PORTER",
        summary="Vague ticket",
        description="",
        persona="silas",
        correlation_id="corr-90",
    )

    with pytest.raises(JulesDispatchError, match="missing required specification context"):
        dispatcher.build_work_order(issue=incomplete_issue, target_paths=[])
