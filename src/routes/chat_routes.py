"""
Chat routes.

Handles interaction with the First-Serving Porter conversational agent.
"""

import logging
from flask import Blueprint, jsonify, request

from src.agents.first_serving_porter import run_first_serving_porter
from src.routes.auth_middleware import require_api_key
from src.services.tenant_context import contains_null_bytes, resolve_request_tenant

chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger("APP_ROUTER")

_MAX_CHAT_MESSAGE_LEN = 10000


@chat_bp.route("/chat/porter", methods=["POST", "OPTIONS"])
@require_api_key
def chat_porter():
    """Handle chat interaction with the First-Serving Porter agent."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or "message" not in data:
            return jsonify({"error": "Message required"}), 400

        user_msg = data["message"]
        if (
            not isinstance(user_msg, str)
            or not user_msg.strip()
            or len(user_msg) > _MAX_CHAT_MESSAGE_LEN
            or contains_null_bytes(user_msg)
        ):
            return jsonify({"error": "Invalid message payload"}), 400

        tenant = resolve_request_tenant(request)
        if not tenant:
            return jsonify({"error": "No email associated with token"}), 400

        logger.info(
            "Received Porter chat message for %s (username=%s).",
            tenant.user_email,
            tenant.username,
        )
        result = run_first_serving_porter(
            user_msg, username=tenant.username, user_email=tenant.user_email
        )
        return jsonify(result)

    except Exception as exc:
        logger.error("Error in First-Serving Porter chat: %s", exc, exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500


@chat_bp.route("/chat/welcome", methods=["GET", "OPTIONS"])
@require_api_key
def chat_welcome():
    """Generate a dynamic welcome message on dashboard load."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        tenant = resolve_request_tenant(request)
        if not tenant:
            return jsonify({"error": "No email associated with token"}), 400

        logger.info(
            "Generating dynamic welcome message for %s (username=%s).",
            tenant.user_email,
            tenant.username,
        )
        user_msg = (
            "Please provide a short, welcoming 1-2 sentence greeting for the user acknowledging "
            "their current identity graph stability. Keep it extremely brief and helpful."
        )
        result = run_first_serving_porter(
            user_msg, username=tenant.username, user_email=tenant.user_email
        )
        return jsonify(result)

    except Exception as exc:
        logger.error("Error in First-Serving Porter welcome: %s", exc, exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500
