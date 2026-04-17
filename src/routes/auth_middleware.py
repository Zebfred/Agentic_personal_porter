"""
Authentication middleware for Flask routes.

Provides the `require_api_key` decorator used by all protected blueprints.
Supports both raw API key (for backend scripts) and JWT tokens (for the frontend UI).

WHY lazy reads: Environment variables are read inside the decorator function
(at request time) rather than at module import time. This guarantees that
dotenv has already been called by the app factory regardless of import
ordering, and makes testing with monkeypatched env vars work correctly.
"""
import os
import hmac
import jwt
from functools import wraps
from flask import request, jsonify, make_response


def require_api_key(f):
    """Decorator that enforces API key or JWT authentication on a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Let CORS preflight through cleanly
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin", "*"))
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
            response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
            return response, 204

        # Read secrets at request time, not import time
        api_key = os.environ.get("PORTER_API_KEY", "")
        jwt_secret = os.environ.get("JWT_SECRET", "")

        supplied_key = request.headers.get("Authorization")
        if not supplied_key:
            return jsonify({"error": "Unauthorized: Missing Authorization header"}), 401

        token_str = supplied_key.replace("Bearer ", "")

        # Check if it's the raw API Key (used by background python scripts usually)
        if api_key and hmac.compare_digest(token_str, api_key):
            return f(*args, **kwargs)

        # Try checking if it's a valid JWT from the frontend login UI
        if jwt_secret:
            try:
                decoded = jwt.decode(token_str, jwt_secret, algorithms=["HS256"])
                if decoded.get("role") == "admin":
                    return f(*args, **kwargs)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Unauthorized: Token expired"}), 401
            except jwt.InvalidTokenError:
                pass

        return jsonify({"error": "Unauthorized: Invalid credentials"}), 401
    return decorated_function
