"""
User routes.

Handles user profile and Nexus Guild invitation.
"""
import logging
from flask import Blueprint, request, jsonify

from src.database.mongo_storage import SovereignMongoStorage
from src.routes.auth_middleware import require_api_key

user_bp = Blueprint('user', __name__)
logger = logging.getLogger("APP_ROUTER")

@user_bp.route('/profile', methods=['GET'])
@require_api_key
def get_profile():
    """
    Returns the currently authenticated user's profile and invite status.
    """
    user_email = request.user_email
    if not user_email:
        return jsonify({"error": "No email associated with token"}), 400

    try:
        storage = SovereignMongoStorage()
        user_doc = storage.get_user_by_email(user_email)
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
            
        # Don't return sensitive stuff if any
        return jsonify({
            "email": user_doc.get("email"),
            "profile": user_doc.get("profile"),
            "guild_invite_status": user_doc.get("guild_invite_status", "pending"),
            "role": user_doc.get("role", "user"),
            "privacy_opt_in_analytics": user_doc.get("privacy_opt_in_analytics", False)
        })
    except Exception as e:
        logger.error(f"Error fetching profile for {user_email}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/invite', methods=['POST'])
@require_api_key
def update_invite_status():
    """
    Accepts or declines the Nexus Guild invitation.
    """
    user_email = request.user_email
    if not user_email:
        return jsonify({"error": "No email associated with token"}), 400

    data = request.get_json()
    action = data.get("action")
    
    if action not in ["accept", "decline"]:
        return jsonify({"error": "Invalid action. Must be 'accept' or 'decline'"}), 400

    try:
        storage = SovereignMongoStorage()
        status = "accepted" if action == "accept" else "declined"
        success = storage.update_guild_invite_status(user_email, status)
        
        if success:
            logger.info(f"User {user_email} {status} the Nexus Guild invitation.")
            return jsonify({
                "message": f"Invitation {status}.",
                "guild_invite_status": status
            })
        else:
            return jsonify({"error": "Failed to update invitation status"}), 500
            
    except Exception as e:
        logger.error(f"Error updating invite for {user_email}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/opt_in_analytics', methods=['POST'])
@require_api_key
def update_analytics_opt_in():
    """
    Updates the user's data privacy opt-in for admin analytics.
    """
    user_email = request.user_email
    if not user_email:
        return jsonify({"error": "No email associated with token"}), 400

    data = request.get_json()
    opt_in = data.get("opt_in")
    
    if opt_in is None:
        return jsonify({"error": "opt_in boolean required"}), 400

    try:
        storage = SovereignMongoStorage()
        success = storage.toggle_privacy_opt_in(user_email, bool(opt_in))
        
        if success:
            return jsonify({
                "message": "Privacy preferences updated.",
                "privacy_opt_in_analytics": bool(opt_in)
            })
        else:
            return jsonify({"error": "Failed to update privacy preferences"}), 500
            
    except Exception as e:
        logger.error(f"Error updating privacy opt-in for {user_email}: {e}")
        return jsonify({"error": "Internal server error"}), 500
