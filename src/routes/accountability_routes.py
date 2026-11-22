"""Flask Blueprint for North Star Accountability & Weekly Streak Engine (004)."""

import logging
import re

from flask import Blueprint, Response, jsonify, request
from pydantic import ValidationError

from src.database.mongo_client.connection import MongoConnectionManager
from src.routes.auth_middleware import require_api_key
from src.schemas.accountability_models import (
    GraceWindowRequest,
    PillarUpsertBatchRequest,
    ReconCheckInRequest,
)
from src.services.accountability_service import (
    build_accountability_dashboard,
    get_pillars_payload,
    log_recon_entry,
    save_pillars_batch,
    set_grace_window,
)

accountability_bp = Blueprint("accountability", __name__)
logger = logging.getLogger("APP_ROUTER")
_ISO_WEEK_QUERY_RE = re.compile(r"^\d{4}-W(?:0[1-9]|[1-4]\d|5[0-3])$")


def _extract_user_email() -> str | None:
    """Read authenticated tenant email injected by require_api_key."""
    email = getattr(request, "user_email", None)
    return str(email).strip() if isinstance(email, str) and email.strip() else None


@accountability_bp.route("/pillars", methods=["GET"])
@require_api_key
def get_pillars() -> tuple[Response, int]:
    """List active North Star Pillars for the authenticated Hero."""
    user_email = _extract_user_email()
    if not user_email:
        return jsonify({"error": "No email associated with token"}), 400
    try:
        db = MongoConnectionManager.get_db()
        return jsonify(get_pillars_payload(db, user_email)), 200
    except Exception as exc:
        logger.error("Accountability GET /pillars error for %s: %s", user_email, exc)
        return jsonify({"error": "Internal server error"}), 500


@accountability_bp.route("/pillars", methods=["PUT"])
@require_api_key
def put_pillars() -> tuple[Response, int]:
    """Upsert up to 6 tenant-scoped North Star Pillars."""
    user_email = _extract_user_email()
    if not user_email:
        return jsonify({"error": "No email associated with token"}), 400
    try:
        batch = PillarUpsertBatchRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors()}), 422
    try:
        db = MongoConnectionManager.get_db()
        return jsonify(save_pillars_batch(db, user_email, batch.pillars)), 200
    except Exception as exc:
        logger.error("Accountability PUT /pillars error for %s: %s", user_email, exc)
        return jsonify({"error": "Internal server error"}), 500


@accountability_bp.route("/recon-checkin", methods=["POST"])
@require_api_key
def post_recon_entry() -> tuple[Response, int]:
    """Log an idempotent 20-Second Recon win against an active pillar."""
    user_email = _extract_user_email()
    if not user_email:
        return jsonify({"error": "No email associated with token"}), 400
    try:
        payload = ReconCheckInRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors()}), 422
    try:
        db = MongoConnectionManager.get_db()
        body, status_code = log_recon_entry(db, user_email, payload)
        return jsonify(body), status_code
    except Exception as exc:
        logger.error("Accountability POST /recon-checkin error for %s: %s", user_email, exc)
        return jsonify({"error": "Internal server error"}), 500


@accountability_bp.route("/streaks", methods=["GET"])
@require_api_key
def get_streaks() -> tuple[Response, int]:
    """Return weekly streak summaries, Grace Mode state, and life harmony ratio."""
    user_email = _extract_user_email()
    if not user_email:
        return jsonify({"error": "No email associated with token"}), 400
    iso_week = request.args.get("iso_week")
    if iso_week and not _ISO_WEEK_QUERY_RE.match(iso_week):
        return jsonify({"error": "iso_week must match YYYY-W01..YYYY-W53."}), 422
    try:
        db = MongoConnectionManager.get_db()
        dashboard = build_accountability_dashboard(db, user_email, iso_week=iso_week)
        return jsonify(dashboard.model_dump(mode="json")), 200
    except Exception as exc:
        logger.error("Accountability GET /streaks error for %s: %s", user_email, exc)
        return jsonify({"error": "Internal server error"}), 500


@accountability_bp.route("/grace-window", methods=["POST"])
@require_api_key
def post_grace_window() -> tuple[Response, int]:
    """Toggle Vacation / Grace Mode for a specific ISO week."""
    user_email = _extract_user_email()
    if not user_email:
        return jsonify({"error": "No email associated with token"}), 400
    try:
        payload = GraceWindowRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors()}), 422
    try:
        db = MongoConnectionManager.get_db()
        return jsonify(set_grace_window(db, user_email, payload)), 200
    except Exception as exc:
        logger.error("Accountability POST /grace-window error for %s: %s", user_email, exc)
        return jsonify({"error": "Internal server error"}), 500


@accountability_bp.route("/export-markdown", methods=["GET"])
@require_api_key
def export_markdown() -> tuple[Response, int]:
    """Export a portable, markdownlint-friendly Accountability snapshot."""
    user_email = _extract_user_email()
    if not user_email:
        return jsonify({"error": "No email associated with token"}), 400
    iso_week = request.args.get("iso_week")
    if iso_week and not _ISO_WEEK_QUERY_RE.match(iso_week):
        return jsonify({"error": "iso_week must match YYYY-W01..YYYY-W53."}), 422
    try:
        db = MongoConnectionManager.get_db()
        dashboard = build_accountability_dashboard(db, user_email, iso_week=iso_week)
        return Response(str(dashboard), status=200, mimetype="text/markdown; charset=utf-8"), 200
    except Exception as exc:
        logger.error("Accountability GET /export-markdown error for %s: %s", user_email, exc)
        return jsonify({"error": "Internal server error"}), 500
