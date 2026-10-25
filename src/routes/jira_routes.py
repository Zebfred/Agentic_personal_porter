"""
Flask Blueprint for the Unified Spec-Kit, Jira, and Jules Bridge (`/api/integrations/*`).

All endpoints enforce `@require_api_key` authentication (`request.user_email`),
validate payloads via Pydantic v2 schemas (`src/schemas/jira_models.py`),
and return sanitized error responses (`Sentinel` & `Archie` compliance).
"""
import logging
from typing import Optional
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from src.database.mongo_client.jira_storage import JiraStorage
from src.database.mongo_client.uuid_manager import UUIDGenerator
from src.integrations.jira_client import JiraClient, JiraClientError
from src.integrations.jules_dispatcher import JulesDispatcher, JulesDispatchError
from src.orchestrators.speckit_jira_bridge import (
    _resolve_default_feature_dir,
    parse_speckit_tasks_markdown,
    sync_feature_to_jira,
)
from src.routes.auth_middleware import require_api_key
from src.schemas.jira_models import (
    JiraIssueRecord,
    JiraSyncRequestSchema,
    JulesDispatchRequestSchema,
    SpecKitPushRequestSchema,
)
from src.utils.path_utils import get_project_root

logger = logging.getLogger("APP_ROUTER")

jira_bp = Blueprint("jira_bp", __name__)


@jira_bp.route("/integrations/jira/sync", methods=["POST", "OPTIONS"])
@require_api_key
def sync_jira_issues():
    """
    Bi-directional Jira synchronization endpoint:
    1. Flushes any `pending_upstream` tenant issues to Jira when `flush_pending=True`.
    2. Pulls active Jira issues via JQL and persists them in batched `bulk_write`.
    3. Merges synchronized issues into the Neo4j Identity Graph (`:Quest:Intention`).
    """
    user_email = getattr(request, "user_email", "anonymous@localhost")
    raw_body = request.get_json(silent=True) or {}

    try:
        validated = JiraSyncRequestSchema.model_validate(raw_body)
    except ValidationError as exc:
        return jsonify({"error": "Invalid request payload", "details": exc.errors()}), 400

    try:
        client = JiraClient.from_env(project_key_override=validated.project_key)
    except JiraClientError as exc:
        logger.warning("Jira sync configuration error for %s: %s", user_email, exc)
        return jsonify({"error": str(exc)}), 400

    storage = JiraStorage()
    flushed_count = 0

    if validated.flush_pending:
        pending_records = storage.get_pending_upstream_issues(
            user_email=user_email,
            project_key=client.project_key,
        )
        flushed_updates: list[JiraIssueRecord] = []
        for pending in pending_records:
            try:
                remote_key = client.create_issue(
                    summary=pending.summary,
                    description=pending.description,
                    issue_type=pending.issue_type,
                    project_key=pending.project_key,
                    labels=pending.labels,
                )
                flushed_updates.append(
                    pending.model_copy(
                        update={
                            "jira_key": remote_key,
                            "uuid": UUIDGenerator.generate_for_jira_issue(
                                remote_key, user_email
                            ),
                            "sync_status": "synced",
                        }
                    )
                )
                flushed_count += 1
            except JiraClientError as exc:
                logger.warning("Deferred pending issue %s: %s", pending.jira_key, exc)

        if flushed_updates:
            storage.bulk_upsert_issues(flushed_updates)

    try:
        pulled_records = client.fetch_issues(
            user_email=user_email,
            project_key=client.project_key,
            jql_filter=validated.jql_filter,
            max_results=validated.max_results,
        )
    except JiraClientError as exc:
        logger.error("Jira fetch failed for %s: %s", user_email, exc)
        return jsonify({"error": "Failed to fetch issues from Jira"}), 502

    counts = storage.bulk_upsert_issues(pulled_records)
    storage.merge_issues_to_neo4j(pulled_records)
    corr_id = (
        pulled_records[0].correlation_id
        if pulled_records
        else f"sync-{user_email}"
    )

    return (
        jsonify(
            {
                "status": "success",
                "pulled_count": len(pulled_records),
                "flushed_count": flushed_count,
                "upserted_count": counts["upserted_count"] + counts["modified_count"],
                "correlation_id": corr_id,
            }
        ),
        200,
    )


@jira_bp.route("/integrations/jira/speckit-push", methods=["POST", "OPTIONS"])
@require_api_key
def push_speckit_to_jira():
    """
    Parse `spec.md` and `tasks.md` from the requested feature directory and
    create/update a standardized Jira Epic + child Tasks with `T001`+ deduplication.
    """
    user_email = getattr(request, "user_email", "anonymous@localhost")
    raw_body = request.get_json(silent=True) or {}

    try:
        validated = SpecKitPushRequestSchema.model_validate(raw_body)
    except ValidationError as exc:
        return jsonify({"error": "Invalid request payload", "details": exc.errors()}), 400

    root = get_project_root()
    feature_path = (root / validated.feature_dir).resolve()
    if not str(feature_path).startswith(str(root.resolve())):
        return jsonify({"error": "Invalid feature_dir path boundary"}), 400
    if not (feature_path / "tasks.md").exists():
        return jsonify({"error": "tasks.md not found in feature_dir"}), 404

    client: Optional[JiraClient] = None
    if not validated.dry_run:
        try:
            client = JiraClient.from_env(project_key_override=validated.project_key)
        except JiraClientError as exc:
            logger.warning("Jira client unavailable; queueing locally: %s", exc)

    result = sync_feature_to_jira(
        feature_dir=feature_path,
        user_email=user_email,
        project_key=(validated.project_key or "PORTER").upper(),
        dry_run=validated.dry_run,
        jira_client=client,
    )
    return jsonify(result), 200


@jira_bp.route("/integrations/jules/dispatch", methods=["POST", "OPTIONS"])
@require_api_key
def dispatch_jira_to_jules():
    """
    Format a Jira issue (and optional Spec-Kit task) into a self-contained
    `JulesWorkOrder` with `.jules/<persona>.md` rules and verification gates,
    and optionally invoke `@google/jules`.
    """
    user_email = getattr(request, "user_email", "anonymous@localhost")
    raw_body = request.get_json(silent=True) or {}

    try:
        validated = JulesDispatchRequestSchema.model_validate(raw_body)
    except ValidationError as exc:
        return jsonify({"error": "Invalid request payload", "details": exc.errors()}), 400

    storage = JiraStorage()
    issue = storage.get_issue_by_key(user_email=user_email, jira_key=validated.jira_key)
    target_paths: list[str] = []

    if issue is None:
        root = get_project_root()
        f_dir = (
            (root / validated.feature_dir).resolve()
            if validated.feature_dir
            else _resolve_default_feature_dir()
        )
        tasks_path = f_dir / "tasks.md"
        matched_task = None
        if tasks_path.exists() and validated.task_id:
            tasks = parse_speckit_tasks_markdown(tasks_path, feature_id=f_dir.name)
            matched_task = next(
                (t for t in tasks if t.task_id == validated.task_id), None
            )

        if matched_task is None:
            return (
                jsonify(
                    {
                        "error": f"Issue {validated.jira_key} not found in local staging and no matching task_id found."
                    }
                ),
                404,
            )

        target_paths = matched_task.target_paths
        issue = JiraIssueRecord(
            uuid=UUIDGenerator.generate_for_jira_issue(validated.jira_key, user_email),
            user_email=user_email,
            jira_key=validated.jira_key,
            project_key=validated.jira_key.split("-")[0]
            if not validated.jira_key.startswith("LOCAL-")
            else "PORTER",
            task_id=matched_task.task_id,
            feature_id=f_dir.name,
            summary=matched_task.title,
            description=matched_task.description,
            persona=matched_task.persona,
            correlation_id=f"dispatch-{f_dir.name}-{matched_task.task_id}",
        )

    dispatcher = JulesDispatcher()
    try:
        work_order = dispatcher.build_work_order(
            issue=issue,
            target_paths=target_paths,
            persona_override=validated.persona_override,
            dry_run=validated.dry_run,
        )
        jira_client: Optional[JiraClient] = None
        if not validated.dry_run:
            try:
                jira_client = JiraClient.from_env(project_key_override=issue.project_key)
            except JiraClientError:
                jira_client = None
            work_order = dispatcher.dispatch_work_order(
                work_order=work_order,
                jira_client=jira_client,
            )
    except JulesDispatchError as exc:
        logger.exception("Jules dispatch failed: %s", exc)
        return jsonify({"error": "Unable to dispatch Jira issue to Jules"}), 400

    storage.save_work_order(work_order)
    return (
        jsonify(
            {
                "status": "success",
                "work_order": work_order.model_dump(),
                "jira_annotated": bool(
                    not validated.dry_run and work_order.dispatch_status == "dispatched"
                ),
                "correlation_id": work_order.correlation_id,
            }
        ),
        200,
    )
