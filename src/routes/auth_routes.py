"""
Authentication routes.

Handles user login and JWT token issuance.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
import jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow

from src.database.mongo_storage import SovereignMongoStorage
from src.integrations.google_calendar_authentication_helper import get_auth_paths

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger("APP_ROUTER")

@auth_bp.route('/config', methods=['GET'])
def get_config():
    """
    Returns public configuration needed by the frontend.
    """
    return jsonify({
        "google_client_id": os.environ.get("GOOGLE_CLIENT_USER_LOGIN_ID", "").strip("\"'")
    })

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    """
    Validates a Google OAuth ID token, provisions the user, and issues a JWT.
    Grants the 'user' role and 'hero' account type.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()

        if 'credential' not in data:
            return jsonify({"error": "Google ID token (credential) required"}), 400

        token_credential = data['credential']

        # Read secrets
        google_client_id = os.environ.get("GOOGLE_CLIENT_USER_LOGIN_ID", "").strip("\"'")
        jwt_secret = os.environ.get("JWT_SECRET")

        if not jwt_secret:
            logger.error("CRITICAL SECURITY ERROR: JWT_SECRET environment variable is missing.")
            return jsonify({"error": "Server configuration error"}), 500

        if not google_client_id:
            logger.error("GOOGLE_CLIENT_USER_LOGIN_ID is not configured in the environment.")
            return jsonify({"error": "Server configuration error"}), 500

        # Verify Google Token
        try:
            idinfo = id_token.verify_oauth2_token(
                token_credential,
                google_requests.Request(),
                google_client_id
            )
        except ValueError as e:
            logger.warning(f"Invalid Google ID token: {e}")
            return jsonify({"error": "Invalid token"}), 401

        # Extract identity
        email = idinfo.get('email')
        profile_data = {
            "name": idinfo.get('name'),
            "picture": idinfo.get('picture'),
            "given_name": idinfo.get('given_name')
        }

        # Provision/update user in Mongo to get latest status
        username = "Hero"
        try:
            storage = SovereignMongoStorage()
            user_doc = storage.get_or_create_user(email, profile_data)
            username = user_doc.get("username", "Hero")
        except Exception as db_err:
            logger.error(f"Failed to sync user {email} to MongoDB: {db_err}")

        # Always user role for standard portal
        role = "user"
        account_type = "hero"

        # Generate internal JWT valid for 24 hours
        expiration = datetime.now(timezone.utc) + timedelta(hours=24)
        internal_token = jwt.encode(
            {
                "role": role,
                "account_type": account_type,
                "email": email,
                "username": username,
                "exp": expiration,
                "profile": profile_data
            },
            jwt_secret,
            algorithm="HS256"
        )

        return jsonify({
            "token": internal_token,
            "role": role,
            "account_type": account_type,
            "message": "Login successful"
        })

    except Exception as e:
        logger.error(f"Error during user login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/login/code', methods=['POST', 'OPTIONS'])
def login_code():
    """
    Validates a Google OAuth authorization code, provisions the user, 
    saves the refresh token, and issues a JWT.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()

        if 'code' not in data:
            return jsonify({"error": "Google authorization code required"}), 400

        auth_code = data['code']
        jwt_secret = os.environ.get("JWT_SECRET")
        if not jwt_secret:
            logger.error("CRITICAL SECURITY ERROR: JWT_SECRET environment variable is missing.")
            return jsonify({"error": "Server configuration error"}), 500
        paths = get_auth_paths()

        try:
            # Google sometimes returns extra scopes (like calendar.readonly).
            # We must relax strict checking so requests_oauthlib doesn't crash.
            os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

            client_id = os.environ.get("GOOGLE_CLIENT_USER_LOGIN_ID", "").strip("\"'")
            client_secret = os.environ.get("GOOGLE_CLIENT_USER_SECRET", "").strip("\"'")

            if client_id and client_secret:
                client_config = {
                    "web": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                }
                flow = Flow.from_client_config(
                    client_config,
                    scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/calendar']
                )
            elif os.path.exists(paths["credentials"]):
                flow = Flow.from_client_secrets_file(
                    paths["credentials"],
                    scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/calendar']
                )
            else:
                logger.error("Missing Google credentials.json and environment secrets")
                return jsonify({"error": "Server configuration error"}), 500
            flow.redirect_uri = 'postmessage'
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials
        except Exception as e:
            logger.error(f"Failed to exchange auth code: {e}")
            return jsonify({"error": "Failed to exchange authorization code"}), 401

        # Verify Google Token to extract identity
        google_client_id = os.environ.get("GOOGLE_CLIENT_USER_LOGIN_ID", "").strip("\"'")
        try:
            idinfo = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                google_client_id
            )
        except ValueError as e:
            logger.warning(f"Invalid Google ID token from exchanged code: {e}")
            return jsonify({"error": "Invalid token identity"}), 401

        email = idinfo.get('email')
        profile_data = {
            "name": idinfo.get('name'),
            "picture": idinfo.get('picture'),
            "given_name": idinfo.get('given_name')
        }

        # Provision/update user in Mongo
        username = "Hero"
        try:
            storage = SovereignMongoStorage()
            user_doc = storage.get_or_create_user(email, profile_data)
            username = user_doc.get("username", "Hero")
            # Save refresh token if available
            if credentials.refresh_token:
                storage.update_user_sync_preferences(email, True, credentials.refresh_token)
        except Exception as db_err:
            logger.error(f"Failed to sync user {email} to MongoDB: {db_err}")

        role = "user"
        account_type = "hero"

        # Generate internal JWT valid for 24 hours
        expiration = datetime.now(timezone.utc) + timedelta(hours=24)
        internal_token = jwt.encode(
            {
                "role": role,
                "account_type": account_type,
                "email": email,
                "username": username,
                "exp": expiration,
                "profile": profile_data
            },
            jwt_secret,
            algorithm="HS256"
        )

        return jsonify({
            "token": internal_token,
            "role": role,
            "account_type": account_type,
            "message": "Login successful"
        })

    except Exception as e:
        logger.error(f"Error during user code login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/nexus/login', methods=['POST', 'OPTIONS'])
def nexus_login():
    """
    Validates a Google OAuth ID token for the Nexus-Guild admin portal.
    STRICTLY restricts access to @nexus-ds-ml-consulting.com accounts.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()

        if 'credential' not in data:
            return jsonify({"error": "Google ID token (credential) required"}), 400

        token_credential = data['credential']

        google_client_id = os.environ.get("GOOGLE_CLIENT_USER_LOGIN_ID", "").strip("\"'")
        jwt_secret = os.environ.get("JWT_SECRET")

        if not jwt_secret:
            logger.error("CRITICAL SECURITY ERROR: JWT_SECRET environment variable is missing.")
            return jsonify({"error": "Server configuration error"}), 500

        if not google_client_id:
            logger.error("GOOGLE_CLIENT_USER_LOGIN_ID is not configured in the environment.")
            return jsonify({"error": "Server configuration error"}), 500

        # Verify Google Token
        try:
            idinfo = id_token.verify_oauth2_token(
                token_credential,
                google_requests.Request(),
                google_client_id
            )
        except ValueError as e:
            logger.warning(f"Invalid Google ID token on admin login: {e}")
            return jsonify({"error": "Invalid token"}), 401

        email = idinfo.get('email', '')

        # STRICT ORG CHECK
        if not email.endswith('@nexus-ds-ml-consulting.com'):
            logger.warning(f"SECURITY AUDIT: Unauthorized admin login attempt from {email} via {request.remote_addr}")
            return jsonify({"error": "Unauthorized: Must be a Nexus-Guild domain account."}), 403

        profile_data = {
            "name": idinfo.get('name'),
            "picture": idinfo.get('picture'),
            "given_name": idinfo.get('given_name')
        }

        # Provision/update user in Mongo
        try:
            storage = SovereignMongoStorage()
            user_doc = storage.get_or_create_user(email, profile_data)
        except Exception as db_err:
            logger.error(f"Failed to sync admin {email} to MongoDB: {db_err}")

        role = "admin"
        account_type = "guild"

        # Generate internal JWT valid for 24 hours
        expiration = datetime.now(timezone.utc) + timedelta(hours=24)
        internal_token = jwt.encode(
            {
                "role": role,
                "account_type": account_type,
                "email": email,
                "exp": expiration,
                "profile": profile_data
            },
            jwt_secret,
            algorithm="HS256"
        )

        logger.info(f"SECURITY AUDIT: Nexus Guild Admin login via IP {request.remote_addr} for email {email}")

        return jsonify({
            "token": internal_token,
            "role": role,
            "account_type": account_type,
            "message": "Admin login successful"
        })

    except Exception as e:
        logger.error(f"Error during admin login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/nexus/login/code', methods=['POST', 'OPTIONS'])
def nexus_login_code():
    """
    Validates a Google OAuth authorization code for the Nexus-Guild admin portal.
    STRICTLY restricts access to @nexus-ds-ml-consulting.com accounts.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()

        if 'code' not in data:
            return jsonify({"error": "Google authorization code required"}), 400

        auth_code = data['code']
        jwt_secret = os.environ.get("JWT_SECRET")
        if not jwt_secret:
            logger.error("CRITICAL SECURITY ERROR: JWT_SECRET environment variable is missing.")
            return jsonify({"error": "Server configuration error"}), 500
        paths = get_auth_paths()

        try:
            client_id = os.environ.get("GOOGLE_CLIENT_USER_LOGIN_ID", "").strip("\"'")
            client_secret = os.environ.get("GOOGLE_CLIENT_USER_SECRET", "").strip("\"'")

            if client_id and client_secret:
                client_config = {
                    "web": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                }
                flow = Flow.from_client_config(
                    client_config,
                    scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/calendar']
                )
            elif os.path.exists(paths["credentials"]):
                flow = Flow.from_client_secrets_file(
                    paths["credentials"],
                    scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/calendar']
                )
            else:
                logger.error("Missing Google credentials.json and environment secrets")
                return jsonify({"error": "Server configuration error"}), 500
            flow.redirect_uri = 'postmessage'
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials
        except Exception as e:
            logger.error(f"Failed to exchange admin auth code: {e}")
            return jsonify({"error": "Failed to exchange authorization code"}), 401

        # Verify Google Token to extract identity
        google_client_id = os.environ.get("GOOGLE_CLIENT_USER_LOGIN_ID", "").strip("\"'")
        try:
            idinfo = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                google_client_id
            )
        except ValueError as e:
            logger.warning(f"Invalid Google ID token on admin login: {e}")
            return jsonify({"error": "Invalid token"}), 401

        email = idinfo.get('email', '')

        # STRICT ORG CHECK
        if not email.endswith('@nexus-ds-ml-consulting.com'):
            logger.warning(f"SECURITY AUDIT: Unauthorized admin login attempt from {email} via {request.remote_addr}")
            return jsonify({"error": "Unauthorized: Must be a Nexus-Guild domain account."}), 403

        profile_data = {
            "name": idinfo.get('name'),
            "picture": idinfo.get('picture'),
            "given_name": idinfo.get('given_name')
        }

        # Provision/update user in Mongo
        try:
            storage = SovereignMongoStorage()
            user_doc = storage.get_or_create_user(email, profile_data)
            if credentials.refresh_token:
                storage.update_user_sync_preferences(email, True, credentials.refresh_token)
        except Exception as db_err:
            logger.error(f"Failed to sync admin {email} to MongoDB: {db_err}")

        role = "admin"
        account_type = "guild"

        # Generate internal JWT valid for 24 hours
        expiration = datetime.now(timezone.utc) + timedelta(hours=24)
        internal_token = jwt.encode(
            {
                "role": role,
                "account_type": account_type,
                "email": email,
                "exp": expiration,
                "profile": profile_data
            },
            jwt_secret,
            algorithm="HS256"
        )

        logger.info(f"SECURITY AUDIT: Nexus Guild Admin login via IP {request.remote_addr} for email {email}")

        return jsonify({
            "token": internal_token,
            "role": role,
            "account_type": account_type,
            "message": "Admin login successful"
        })

    except Exception as e:
        logger.error(f"Error during admin code login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
