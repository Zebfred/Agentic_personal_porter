"""
Chat routes.

Handles interaction with the First-Serving Porter conversational agent.
"""
import logging
from flask import Blueprint, request, jsonify

from src.routes.auth_middleware import require_api_key
from src.agents.first_serving_porter import run_first_serving_porter

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger("APP_ROUTER")


@chat_bp.route('/chat/porter', methods=['POST', 'OPTIONS'])
@require_api_key
def chat_porter():
    """
    Handles chat interaction with the First-Serving Porter agent.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Message required"}), 400

        user_msg = data['message']
        logger.info("Received Porter chat message.")

        result = run_first_serving_porter(user_msg)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in First-Serving Porter chat: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
