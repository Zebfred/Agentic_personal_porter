import pytest
import importlib

def test_neo4j_module_imports():
    """Verify the modular neo4j_client structure loads correctly"""
    try:
        import src.database.neo4j_client as client
        assert hasattr(client, 'get_driver')
        assert hasattr(client, 'get_valuable_detours')
        assert hasattr(client, 'log_to_neo4j')
    except ImportError as e:
        pytest.fail(f"Could not import neo4j_client modules: {str(e)}")

def test_read_operations_exist():
    try:
        from src.database.neo4j_client.read_operations import get_goal_progress, get_user_patterns
        assert callable(get_goal_progress)
        assert callable(get_user_patterns)
    except ImportError as e:
        pytest.fail(f"Failed to import read operations: {str(e)}")

def test_write_operations_exist():
    try:
        from src.database.neo4j_client.write_operations import create_identity_graph, create_goal
        assert callable(create_identity_graph)
        assert callable(create_goal)
    except ImportError as e:
        pytest.fail(f"Failed to import write operations: {str(e)}")
