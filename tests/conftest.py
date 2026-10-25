import os
import pytest
import mongomock

# Mock critical environment variables for test collection so that top-level module imports
# in app.py and LangChain don't crash when .env is missing (e.g. in GitHub Actions CI/CD).
os.environ.setdefault("PORTER_API_KEY", "dummy_test_porter_api_key")
os.environ.setdefault("PORTER_ADMIN_KEY", "default_dev_key")
os.environ.setdefault("JWT_SECRET", "dummy_test_jwt_secret_key")
os.environ.setdefault("GROQ_API_KEY", "dummy_test_groq_api_key")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/gcal-data")


from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def mock_mongo(monkeypatch):
    """Provides a zero-cost, ephemeral in-memory MongoDB for tests."""
    mock_client = mongomock.MongoClient()
    monkeypatch.setattr(
        "src.database.mongo_storage.MongoClient", lambda *args, **kwargs: mock_client
    )
    try:
        monkeypatch.setattr(
            "src.database.mongo_client.connection.MongoClient", lambda *args, **kwargs: mock_client
        )
    except Exception:
        pass
    return mock_client


@pytest.fixture(autouse=True)
def mock_neo4j(monkeypatch):
    """Prevents slow network timeouts to remote Neo4j in unit tests."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session
    mock_session.execute_read.return_value = []
    mock_session.execute_write.return_value = []
    try:
        monkeypatch.setattr("src.database.neo4j_client.connection.get_driver", lambda: mock_driver)
    except Exception:
        pass
    return mock_driver
