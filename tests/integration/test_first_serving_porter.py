import pytest
from unittest.mock import patch, MagicMock
from src.app import app
import os

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch('src.app.run_first_serving_porter')
def test_porter_chat_route(mock_run_porter, client):
    # Mock the return value of the agent
    mock_run_porter.return_value = {
        "response": "Hello, I am the Porter. I have marked that for update.",
        "transparency_logs": ["[TRANSPARENCY HANDOFF] Marked hero_origin.json for update regarding: Motivation"]
    }

    # Make request with default dev key to pass auth
    response = client.post(
        '/api/chat/porter',
        json={'message': 'Update my motivation.'},
        headers={'Authorization': f'Bearer {os.environ.get("PORTER_API_KEY", "default_dev_key")}'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["response"] == "Hello, I am the Porter. I have marked that for update."
    assert len(data["transparency_logs"]) == 1
    mock_run_porter.assert_called_once_with('Update my motivation.')

@patch('src.app.run_first_serving_porter')
def test_porter_chat_route_missing_message(mock_run_porter, client):
    response = client.post(
        '/api/chat/porter',
        json={},
        headers={'Authorization': f'Bearer {os.environ.get("PORTER_API_KEY", "default_dev_key")}'}
    )
    assert response.status_code == 400
    mock_run_porter.assert_not_called()
