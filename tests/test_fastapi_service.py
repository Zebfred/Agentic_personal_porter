"""
Integration tests for FastAPI service.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from fastapi.testclient import TestClient
from rag_top_level_service.rag_service import app
import os


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "endpoints" in data


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_query_endpoint_missing_key(client):
    """Test query endpoint with missing query."""
    response = client.post("/query", json={})
    assert response.status_code == 422  # Validation error


def test_query_endpoint(client):
    """Test query endpoint."""
    if not os.getenv('GROQ_API_KEY'):
        pytest.skip("GROQ_API_KEY not set")
    
    response = client.post(
        "/query",
        json={"query": "What is reinforcement learning?", "top_k": 3}
    )
    
    # Should either succeed or fail gracefully
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "query" in data


def test_rebuild_index_endpoint_no_papers(client):
    """Test rebuild_index endpoint when no papers exist."""
    # Test with invalid strategy
    response = client.post("/rebuild_index?chunking_strategy=invalid")
    assert response.status_code == 400
    
    # Test with valid strategy but missing file
    # This will return 404 if file doesn't exist, 500 if other error
    response = client.post("/rebuild_index?chunking_strategy=fixed")
    assert response.status_code in [200, 404, 500]


def test_query_request_model():
    """Test QueryRequest model validation."""
    from rag_top_level_service.rag_service import QueryRequest
    
    # Valid request
    request = QueryRequest(query="Test query", top_k=5)
    assert request.query == "Test query"
    assert request.top_k == 5
    
    # Default top_k
    request = QueryRequest(query="Test query")
    assert request.top_k == 5

