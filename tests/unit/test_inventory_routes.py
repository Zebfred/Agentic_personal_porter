import pytest
import os
from unittest.mock import patch
from flask import Flask

# Set dummy environment variables to avoid real DB connections in imports
os.environ.setdefault("NEO4J_URI", "bolt://dummy:7687")
os.environ.setdefault("GOOGLE_CLIENT_USER_LOGIN_ID", "dummy")

from src.routes.inventory_routes import inventory_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(inventory_bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()


def test_get_graph_data_success_default_limit(client):
    """
    Test that GET /graph_data successfully fetches graph data with the default limit (500).
    """
    return_val = {"nodes": [{"id": 1, "label": "Node"}], "edges": []}
    mock_import = mock_neo4j_read_operations_import(return_val, limit=500)
    original_import = builtins.__import__

    try:
        builtins.__import__ = mock_import

        # Override environment variables manually instead of patching
        os.environ["PORTER_ADMIN_KEY"] = "dummy_api_key"

        response = client.get(
            '/graph_data',
            headers={"Authorization": "Bearer dummy_api_key"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data == return_val
    finally:
        builtins.__import__ = original_import

def test_get_graph_data_success_custom_limit(client):
    """
    Test that GET /graph_data successfully fetches graph data with a custom limit.
    """
    return_val = {"nodes": [{"id": 1, "label": "Node"}], "edges": []}
    mock_import = mock_neo4j_read_operations_import(return_val, limit=100)
    original_import = builtins.__import__

    try:
        builtins.__import__ = mock_import

        # Override environment variables manually instead of patching
        os.environ["PORTER_ADMIN_KEY"] = "dummy_api_key"

        response = client.get(
            '/graph_data?limit=100',
            headers={"Authorization": "Bearer dummy_api_key"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data == return_val
    finally:
        builtins.__import__ = original_import

def test_get_graph_data_error_handling(client):
    """
    Test that GET /graph_data correctly handles exceptions from get_full_graph_topology.
    """
    return_val = Exception("Database connection failed")
    mock_import = mock_neo4j_read_operations_import(return_val, limit=500)
    original_import = builtins.__import__

    try:
        builtins.__import__ = mock_import

        # Override environment variables manually instead of patching
        os.environ["PORTER_ADMIN_KEY"] = "dummy_api_key"

        response = client.get(
            '/graph_data',
            headers={"Authorization": "Bearer dummy_api_key"}
        )

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Database connection failed"
    finally:
        builtins.__import__ = original_import
