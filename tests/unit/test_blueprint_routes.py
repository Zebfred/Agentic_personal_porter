"""
Tests for the Flask Blueprint refactoring.

Verifies that:
1. The app factory creates the Flask app correctly
2. All expected routes exist and map to the correct URLs
3. Auth middleware blocks unauthenticated requests
4. Auth middleware allows valid API key and JWT
5. Login endpoint issues valid JWTs
6. Blueprint modules import without errors
"""
import os
import pytest
import jwt
from datetime import datetime, timedelta

# Ensure env vars are set BEFORE importing the app, just like production
os.environ.setdefault("PORTER_API_KEY", "test-api-key-for-ci")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-ci")
os.environ.setdefault("HERO_NAME", "TestHero")

from src.app import create_app


@pytest.fixture
def app():
    """Create a fresh app instance for each test."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


# ======================================================================
#  Route Existence Tests — verify 1:1 mapping after the Blueprint split
# ======================================================================

class TestRouteMapping:
    """Verify every frontend-expected URL is still registered."""

    EXPECTED_ROUTES = [
        # Static pages
        ('/', ['GET']),
        ('/index.html', ['GET']),
        ('/adventure_log', ['GET']),
        ('/Adventure_Time_log.html', ['GET']),
        ('/journal_review', ['GET']),
        ('/journal_review.html', ['GET']),
        ('/oracle_predictions', ['GET']),
        ('/Oracle_predictions.html', ['GET']),
        ('/inventory', ['GET']),
        ('/inventory.html', ['GET']),
        ('/artifacts', ['GET']),
        ('/artifacts.html', ['GET']),
        ('/login', ['GET']),
        ('/login.html', ['GET']),
        ('/graph_explorer', ['GET']),
        ('/graph_explorer.html', ['GET']),
        # Static assets
        ('/js/<path:filename>', ['GET']),
        ('/css/<path:filename>', ['GET']),
        # Auth
        ('/api/login', ['POST']),
        # Journal
        ('/api/save_log', ['POST']),
        ('/api/logs', ['GET']),
        ('/process_journal', ['POST']),
        # Chat
        ('/api/chat/porter', ['POST']),
        # Calendar
        ('/get_calendar_events', ['GET']),
        # Inventory & artifacts
        ('/api/inventory', ['GET']),
        ('/api/artifacts/<artifact_name>', ['GET', 'POST']),
        ('/api/graph_data', ['GET']),
        # Admin
        ('/api/calendar/user_sync', ['POST']),
        ('/api/admin/vector_sync', ['POST']),
        ('/api/admin/inject_foundation', ['POST']),
        ('/api/wake_infrastructure', ['POST']),
        ('/api/nexus/login', ['POST']),
    ]

    def test_all_expected_routes_exist(self, app):
        """Every URL the frontend depends on must exist in the app's route map."""
        registered = {}
        for rule in app.url_map.iter_rules():
            methods = rule.methods - {'HEAD', 'OPTIONS'}
            registered[rule.rule] = sorted(methods)

        missing = []
        for url, expected_methods in self.EXPECTED_ROUTES:
            if url not in registered:
                missing.append(f"MISSING ROUTE: {url}")
            else:
                for method in expected_methods:
                    if method not in registered[url]:
                        missing.append(f"MISSING METHOD: {method} on {url}")

        assert not missing, f"Route mapping broken after refactor:\n" + "\n".join(missing)

    def test_route_count_sanity(self, app):
        """Ensure we haven't accidentally duplicated or lost routes."""
        # Flask adds a default /static/<path:filename> route; we expect ~45 total
        rule_count = len(list(app.url_map.iter_rules()))
        assert rule_count >= 30, f"Expected >=30 routes, got {rule_count}. Routes may be missing."
        assert rule_count <= 60, f"Expected <=60 routes, got {rule_count}. Possible duplicates."


# ======================================================================
#  Auth Middleware Tests
# ======================================================================

class TestAuthMiddleware:
    """Test the require_api_key decorator via actual route hits."""

    def test_missing_auth_header_returns_401(self, client):
        """A request without Authorization header must be rejected."""
        response = client.get('/api/inventory')
        assert response.status_code == 401
        assert "Unauthorized" in response.get_json()["error"]

    def test_invalid_token_returns_401(self, client):
        """A garbage bearer token must be rejected."""
        response = client.get(
            '/api/inventory',
            headers={"Authorization": "Bearer totally-invalid-token"}
        )
        assert response.status_code == 401

    def test_valid_api_key_returns_success(self, client):
        """A valid raw API key must be accepted."""
        api_key = os.environ.get("PORTER_API_KEY")
        response = client.get(
            '/api/inventory',
            headers={"Authorization": f"Bearer {api_key}"}
        )
        # May fail at the business logic layer (no Neo4j), but NOT at auth
        assert response.status_code != 401, "Auth should have passed with valid API key"

    def test_valid_jwt_returns_success(self, client):
        """A valid JWT with admin role must be accepted."""
        jwt_secret = os.environ.get("JWT_SECRET")
        token = jwt.encode(
            {"role": "admin", "exp": datetime.utcnow() + timedelta(hours=1)},
            jwt_secret,
            algorithm="HS256"
        )
        response = client.get(
            '/api/inventory',
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code != 401, "Auth should have passed with valid JWT"

    def test_expired_jwt_returns_401(self, client):
        """An expired JWT must be rejected."""
        jwt_secret = os.environ.get("JWT_SECRET")
        token = jwt.encode(
            {"role": "admin", "exp": datetime.utcnow() - timedelta(hours=1)},
            jwt_secret,
            algorithm="HS256"
        )
        response = client.get(
            '/api/inventory',
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    def test_options_preflight_passes_without_auth(self, client):
        """CORS preflight OPTIONS requests must pass without auth."""
        response = client.options('/api/inventory')
        assert response.status_code in (200, 204)


# ======================================================================
#  Login Endpoint Tests
# ======================================================================

from unittest.mock import patch

class TestLogin:
    """Test the /api/login JWT issuance endpoint."""

    @patch("src.routes.auth_routes.id_token.verify_oauth2_token")
    @patch("src.routes.auth_routes.SovereignMongoStorage")
    def test_login_with_valid_hero_credential(self, mock_storage, mock_verify, client):
        """Valid Hero Google JWT should return an internal JWT token."""
        mock_verify.return_value = {
            "email": "testuser@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg",
            "given_name": "Test"
        }
        
        # We need to set a dummy GOOGLE_CLIENT_ID in the environment for the test to pass
        os.environ["GOOGLE_CLIENT_ID"] = "test_client_id"
        os.environ["NEXUS_ADMIN_EMAIL"] = "admin@nexus-guild.com"
        
        response = client.post(
            '/api/login',
            json={"credential": "mocked_google_jwt_token"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "token" in data
        assert data["role"] == "user"
        assert data["account_type"] == "hero"

    @patch("src.routes.auth_routes.id_token.verify_oauth2_token")
    @patch("src.routes.auth_routes.SovereignMongoStorage")
    def test_login_with_valid_guild_credential(self, mock_storage, mock_verify, client):
        """Valid Guild Google JWT should return an internal JWT token with admin role."""
        mock_verify.return_value = {
            "email": "admin@nexus-ds-ml-consulting.com",
            "name": "Admin User",
            "picture": "https://example.com/pic.jpg",
            "given_name": "Admin"
        }
        
        os.environ["GOOGLE_CLIENT_ID"] = "test_client_id"
        os.environ["NEXUS_ADMIN_EMAIL"] = "admin@nexus-ds-ml-consulting.com"
        
        response = client.post(
            '/api/nexus/login',
            json={"credential": "mocked_google_jwt_token"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "token" in data
        assert data["role"] == "admin"
        assert data["account_type"] == "guild"

    @patch("src.routes.auth_routes.id_token.verify_oauth2_token")
    def test_login_with_invalid_credential(self, mock_verify, client):
        """Invalid Google JWT should return 401."""
        from google.auth.exceptions import GoogleAuthError
        mock_verify.side_effect = ValueError("Invalid token")
        
        os.environ["GOOGLE_CLIENT_ID"] = "test_client_id"

        response = client.post(
            '/api/login',
            json={"credential": "invalid_token"}
        )
        assert response.status_code == 401

    def test_login_missing_credential(self, client):
        """Missing credential field should return 400."""
        response = client.post(
            '/api/login',
            json={"username": "admin"}
        )
        assert response.status_code == 400


# ======================================================================
#  Blueprint Module Import Tests
# ======================================================================

class TestBlueprintImports:
    """Verify that all route modules can be imported without error."""

    def test_import_static_routes(self):
        from src.routes.static_routes import static_bp
        assert static_bp.name == 'static'

    def test_import_auth_routes(self):
        from src.routes.auth_routes import auth_bp
        assert auth_bp.name == 'auth'

    def test_import_journal_routes(self):
        from src.routes.journal_routes import journal_bp
        assert journal_bp.name == 'journal'

    def test_import_chat_routes(self):
        from src.routes.chat_routes import chat_bp
        assert chat_bp.name == 'chat'

    def test_import_calendar_routes(self):
        from src.routes.calendar_routes import calendar_bp
        assert calendar_bp.name == 'calendar'

    def test_import_inventory_routes(self):
        from src.routes.inventory_routes import inventory_bp
        assert inventory_bp.name == 'inventory'

    def test_import_admin_routes(self):
        from src.routes.admin_routes import admin_bp
        assert admin_bp.name == 'admin'

    def test_import_user_routes(self):
        from src.routes.user_routes import user_bp
        assert user_bp.name == 'user'

    def test_import_auth_middleware(self):
        from src.routes.auth_middleware import require_api_key
        assert callable(require_api_key)
