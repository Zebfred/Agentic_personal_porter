"""
Authentication routes.

Handles user login and JWT token issuance.
DRY-refactored: shared helpers extracted from four near-identical route handlers.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from flask import Blueprint, request, jsonify
import jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow

from src.database.mongo_storage import SovereignMongoStorage
from src.integrations.google_calendar_authentication_helper import get_auth_paths

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger("APP_ROUTER")

# ---------------------------------------------------------------------------
# OAuth scopes shared by all auth-code flows
# ---------------------------------------------------------------------------
_OAUTH_SCOPES: list[str] = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/calendar',
]

_NEXUS_DOMAIN: str = "@nexus-ds-ml-consulting.com"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_auth_secrets() -> tuple[str, str]:
    """Read and validate JWT_SECRET and GOOGLE_CLIENT_USER_LOGIN_ID from env.

    Returns:
        A tuple of (jwt_secret, google_client_id).

    Raises:
        RuntimeError: If either secret is missing, with the appropriate log
            message already emitted so callers can return 500 directly.
    """
    jwt_secret = os.environ.get("JWT_SECRET")
    google_client_id = os.environ.get("GOOGLE_CLIENT_USER_LOGIN_ID", "").strip("\"'")

    if not jwt_secret:
        logger.error("CRITICAL SECURITY ERROR: JWT_SECRET environment variable is missing.")
        raise RuntimeError("Server configuration error")

    if not google_client_id:
        logger.error("GOOGLE_CLIENT_USER_LOGIN_ID is not configured in the environment.")
        raise RuntimeError("Server configuration error")

    return jwt_secret, google_client_id


def _verify_google_token(credential: str, client_id: str) -> dict[str, Any]:
    """Verify a Google OAuth2 ID token.

    Args:
        credential: The raw ID-token string (JWT from Google).
        client_id: The expected audience / OAuth client ID.

    Returns:
        The decoded ``idinfo`` dict from Google.

    Raises:
        ValueError: Propagated from ``id_token.verify_oauth2_token`` when the
            token is invalid, expired, or has an audience mismatch.
    """
    return id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        client_id,
    )


def _extract_profile(idinfo: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Pull the user's email and profile fields from a verified idinfo dict.

    Args:
        idinfo: The dict returned by ``_verify_google_token``.

    Returns:
        A tuple of (email, profile_data) where *profile_data* contains
        ``name``, ``picture``, and ``given_name``.
    """
    email: str = idinfo.get('email', '')
    profile_data: dict[str, Any] = {
        "name": idinfo.get('name'),
        "picture": idinfo.get('picture'),
        "given_name": idinfo.get('given_name'),
    }
    return email, profile_data


def _create_oauth_flow(paths: dict[str, str]) -> Flow:
    """Build a ``google_auth_oauthlib.flow.Flow`` from env vars or credentials.json.

    Prefers environment variables (``GOOGLE_CLIENT_USER_LOGIN_ID`` and
    ``GOOGLE_CLIENT_USER_SECRET``).  Falls back to the credentials.json file
    identified by *paths*.

    Also sets ``OAUTHLIB_RELAX_TOKEN_SCOPE`` so that extra scopes returned by
    Google (e.g. ``calendar.readonly``) don't crash ``requests_oauthlib``.

    Args:
        paths: Dict from ``get_auth_paths()`` containing a ``"credentials"`` key.

    Returns:
        A configured ``Flow`` instance with ``redirect_uri='postmessage'``.

    Raises:
        RuntimeError: If neither env-var credentials nor a credentials.json
            file are available.
    """
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
        flow = Flow.from_client_config(client_config, scopes=_OAUTH_SCOPES)
    elif os.path.exists(paths["credentials"]):
        flow = Flow.from_client_secrets_file(paths["credentials"], scopes=_OAUTH_SCOPES)
    else:
        logger.error("Missing Google credentials.json and environment secrets")
        raise RuntimeError("Missing Google OAuth credentials")

    flow.redirect_uri = 'postmessage'
    return flow


def _provision_user_and_issue_jwt(
    email: str,
    profile_data: dict[str, Any],
    role: str,
    account_type: str,
    jwt_secret: str,
    credentials: Optional[Any] = None,
) -> dict[str, Any]:
    """Provision/update the user in Mongo and issue an internal JWT.

    Args:
        email: The user's verified email address.
        profile_data: Dict with ``name``, ``picture``, ``given_name``.
        role: The role to embed in the JWT (``"user"`` or ``"admin"``).
        account_type: The account type (``"hero"`` or ``"guild"``).
        jwt_secret: The HS256 signing secret.
        credentials: Optional Google OAuth credentials object.  If provided
            and it carries a refresh token, the token is persisted via
            ``SovereignMongoStorage.update_user_sync_preferences``.

    Returns:
        A dict suitable for ``jsonify`` containing ``token``, ``role``,
        ``account_type``, and ``message``.
    """
    # Default username per role
    default_username = "Hero" if role == "user" else email.split("@")[0]
    username = default_username

    try:
        storage = SovereignMongoStorage()
        user_doc = storage.get_or_create_user(email, profile_data)
        username = user_doc.get("username", default_username)

        # Persist refresh token when available (auth-code flows)
        if credentials is not None and getattr(credentials, "refresh_token", None):
            storage.update_user_sync_preferences(email, True, credentials.refresh_token)
    except Exception as db_err:
        logger.error(f"Failed to sync {role} {email} to MongoDB: {db_err}")

    # Generate internal JWT valid for 24 hours
    expiration = datetime.now(timezone.utc) + timedelta(hours=24)
    internal_token = jwt.encode(
        {
            "role": role,
            "account_type": account_type,
            "email": email,
            "username": username,
            "exp": expiration,
            "profile": profile_data,
        },
        jwt_secret,
        algorithm="HS256",
    )

    msg = "Admin login successful" if role == "admin" else "Login successful"
    return {
        "token": internal_token,
        "role": role,
        "account_type": account_type,
        "message": msg,
    }


def _enforce_org_domain(email: str, domain: str) -> None:
    """Verify *email* belongs to the required organisational domain.

    Args:
        email: The user's verified email address.
        domain: The required domain suffix, e.g. ``"@nexus-ds-ml-consulting.com"``.

    Raises:
        PermissionError: If *email* does not end with *domain*, after logging
            the attempt as a security audit event.
    """
    if not email.endswith(domain):
        logger.warning(
            f"SECURITY AUDIT: Unauthorized admin login attempt from {email} "
            f"via {request.remote_addr}"
        )
        raise PermissionError("Unauthorized: Must be a Nexus-Guild domain account.")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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
    """Validates a Google OAuth ID token, provisions the user, and issues a JWT.
    Grants the 'user' role and 'hero' account type.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()
        if 'credential' not in data:
            return jsonify({"error": "Google ID token (credential) required"}), 400

        jwt_secret, google_client_id = _get_auth_secrets()
        idinfo = _verify_google_token(data['credential'], google_client_id)
        email, profile_data = _extract_profile(idinfo)

        return jsonify(_provision_user_and_issue_jwt(
            email, profile_data, "user", "hero", jwt_secret,
        ))

    except RuntimeError:
        return jsonify({"error": "Server configuration error"}), 500
    except ValueError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        logger.error(f"Error during user login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@auth_bp.route('/login/code', methods=['POST', 'OPTIONS'])
def login_code():
    """Validates a Google OAuth authorization code, provisions the user,
    saves the refresh token, and issues a JWT.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()
        if 'code' not in data:
            return jsonify({"error": "Google authorization code required"}), 400

        jwt_secret, google_client_id = _get_auth_secrets()
        flow = _create_oauth_flow(get_auth_paths())
        flow.fetch_token(code=data['code'])
        credentials = flow.credentials

        idinfo = _verify_google_token(credentials.id_token, google_client_id)
        email, profile_data = _extract_profile(idinfo)

        return jsonify(_provision_user_and_issue_jwt(
            email, profile_data, "user", "hero", jwt_secret, credentials,
        ))

    except ValueError:
        return jsonify({"error": "Invalid token"}), 401
    except RuntimeError:
        return jsonify({"error": "Server configuration error"}), 500
    except Exception as e:
        logger.error(f"Error during user code login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@auth_bp.route('/nexus/login', methods=['POST', 'OPTIONS'])
def nexus_login():
    """Validates a Google OAuth ID token for the Nexus-Guild admin portal.
    STRICTLY restricts access to @nexus-ds-ml-consulting.com accounts.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()
        if 'credential' not in data:
            return jsonify({"error": "Google ID token (credential) required"}), 400

        jwt_secret, google_client_id = _get_auth_secrets()
        idinfo = _verify_google_token(data['credential'], google_client_id)
        email, profile_data = _extract_profile(idinfo)
        _enforce_org_domain(email, _NEXUS_DOMAIN)

        result = _provision_user_and_issue_jwt(
            email, profile_data, "admin", "guild", jwt_secret,
        )
        logger.info(f"SECURITY AUDIT: Nexus Guild Admin login via IP {request.remote_addr} for email {email}")
        return jsonify(result)

    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except RuntimeError:
        return jsonify({"error": "Server configuration error"}), 500
    except ValueError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        logger.error(f"Error during admin login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@auth_bp.route('/nexus/login/code', methods=['POST', 'OPTIONS'])
def nexus_login_code():
    """Validates a Google OAuth authorization code for the Nexus-Guild admin portal.
    STRICTLY restricts access to @nexus-ds-ml-consulting.com accounts.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()
        if 'code' not in data:
            return jsonify({"error": "Google authorization code required"}), 400

        jwt_secret, google_client_id = _get_auth_secrets()
        flow = _create_oauth_flow(get_auth_paths())
        flow.fetch_token(code=data['code'])
        credentials = flow.credentials

        idinfo = _verify_google_token(credentials.id_token, google_client_id)
        email, profile_data = _extract_profile(idinfo)
        _enforce_org_domain(email, _NEXUS_DOMAIN)

        result = _provision_user_and_issue_jwt(
            email, profile_data, "admin", "guild", jwt_secret, credentials,
        )
        logger.info(f"SECURITY AUDIT: Nexus Guild Admin login via IP {request.remote_addr} for email {email}")
        return jsonify(result)

    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except RuntimeError:
        return jsonify({"error": "Server configuration error"}), 500
    except ValueError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        logger.error(f"Error during admin code login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
