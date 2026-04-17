"""
Authentication routes.

Handles user login and JWT token issuance.
"""
import os
import hmac
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
import jwt

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger("APP_ROUTER")


@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    """
    Validates the provided password against the PORTER_API_KEY.
    If valid, returns a JWT token valid for 24 hours.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()
        if not data or 'password' not in data:
            return jsonify({"error": "Password required"}), 400

        # Read secrets at request time, not import time
        api_key = os.environ.get("PORTER_API_KEY", "")
        jwt_secret = os.environ.get("JWT_SECRET", "")

        if api_key and hmac.compare_digest(data['password'], api_key):
            # Generate JWT Token valid for 24 hours
            expiration = datetime.utcnow() + timedelta(hours=24)
            token = jwt.encode(
                {"role": "admin", "exp": expiration},
                jwt_secret,
                algorithm="HS256"
            )
            return jsonify({"token": token, "message": "Login successful"})
        else:
            return jsonify({"error": "Invalid password"}), 401

    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
