import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
import json

from src.routes.journal_routes import journal_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(journal_bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@patch('src.routes.journal_routes.SovereignMongoStorage')
@patch('src.routes.auth_middleware.jwt.decode')
@patch('src.routes.auth_middleware.os.environ.get')
def test_save_log_uses_username(mock_env_get, mock_jwt_decode, mock_mongo_class, client):
    """
    Test that POST /api/save_log fetches the username and passes it to save_journal_entry.
    """
    # Setup mock env to allow JWT auth
    def mock_env(key, default=""):
        if key == "JWT_SECRET":
            return "dummy_secret"
        return default
    mock_env_get.side_effect = mock_env

    # Setup mock JWT
    mock_jwt_decode.return_value = {"email": "test@test.com", "role": "user", "account_type": "hero"}

    # Setup mock Mongo Storage
    mock_mongo_instance = MagicMock()
    mock_mongo_class.return_value = mock_mongo_instance
    mock_mongo_instance.get_user_by_email.return_value = {"username": "testuser", "email": "test@test.com"}
    mock_mongo_instance.save_journal_entry.return_value = "dummy_mongo_id"

    # Also mock Neo4j logging to prevent errors since it's instantiated inside
    with patch('src.routes.journal_routes.log_to_neo4j') as mock_neo4j:
        mock_neo4j.return_value = True

        payload = {
            "day": "2026-07-14",
            "timeChunk": "09:00",
            "actual": "Testing log",
            "tag": "Work"
        }

        response = client.post(
            '/api/save_log', 
            data=json.dumps(payload),
            headers={"Content-Type": "application/json", "Authorization": "Bearer dummy_token"}
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.data}"
        
        # Verify save_journal_entry was called with user_id="testuser"
        mock_mongo_instance.save_journal_entry.assert_called_once()
        args, kwargs = mock_mongo_instance.save_journal_entry.call_args
        assert kwargs.get("user_id") == "testuser"

@patch('src.routes.journal_routes.SovereignMongoStorage')
@patch('src.routes.auth_middleware.jwt.decode')
@patch('src.routes.auth_middleware.os.environ.get')
def test_process_journal_uses_username(mock_env_get, mock_jwt_decode, mock_mongo_class, client):
    """
    Test that POST /process_journal fetches the username and passes it to save_agent_reflection.
    """
    # Setup mock env to allow JWT auth
    def mock_env(key, default=""):
        if key == "JWT_SECRET":
            return "dummy_secret"
        return default
    mock_env_get.side_effect = mock_env

    # Setup mock JWT
    mock_jwt_decode.return_value = {"email": "test@test.com", "role": "user", "account_type": "hero"}

    # Setup mock Mongo Storage
    mock_mongo_instance = MagicMock()
    mock_mongo_class.return_value = mock_mongo_instance
    mock_mongo_instance.get_user_by_email.return_value = {"username": "testuser", "email": "test@test.com"}
    mock_mongo_instance.save_agent_reflection.return_value = "dummy_reflection_id"

    # Mock run_porter_reflection
    with patch('src.routes.journal_routes.run_porter_reflection') as mock_run_porter:
        mock_run_porter.return_value = "Mocked reflection text"

        payload = {
            "journal_entry": "This is a summary",
            "log_data": {"day": "2026-07-14"}
        }

        response = client.post(
            '/process_journal', 
            data=json.dumps(payload),
            headers={"Content-Type": "application/json", "Authorization": "Bearer dummy_token"}
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.data}"
        
        # Verify save_agent_reflection was called with user_id="testuser"
        mock_mongo_instance.save_agent_reflection.assert_called_once()
        args, kwargs = mock_mongo_instance.save_agent_reflection.call_args
        saved_data = args[0]
        assert saved_data.get("user_id") == "testuser"
