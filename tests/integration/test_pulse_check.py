import pytest
from unittest.mock import patch, MagicMock
import os
import glob
from pathlib import Path

# Inject dummy keys so the environment check doesn't skip logical blocks
os.environ['LANGCHAIN_API_KEY'] = 'test_key'
os.environ['OPENAI_API_KEY'] = 'test_key'

from helper_scripts.local_pulse_check import run_pulse_check

@patch('helper_scripts.local_pulse_check.load_env_vars')
@patch('helper_scripts.local_pulse_check.SovereignMongoStorage')
@patch('helper_scripts.local_pulse_check.get_driver')
@patch('langsmith.Client')
def test_run_pulse_check_executes_cleanly(mock_ls_client, mock_get_driver, mock_mongo, mock_load_env):
    """
    Ensure the pulse check script runs cleanly without throwing exceptions
    when interacting with its external dependencies: Neo4j, Mongo, and LangSmith.
    """
    # 1. Mock LangSmith Client
    mock_ls_instance = MagicMock()
    mock_run = MagicMock()
    mock_run.name = "Test Run"
    mock_run.error = None
    mock_run.total_tokens = 100
    mock_ls_instance.list_runs.return_value = [mock_run]
    mock_ls_client.return_value = mock_ls_instance

    # 2. Mock Neo4j Driver and Session Context Manager
    mock_driver_instance = MagicMock()
    mock_session = MagicMock()
    
    # execute_read needs to return a dict with "c" and "date" 
    # based on what lambda the pulse script passes
    def side_effect_execute_read(func):
        # We just return a universal mock payload that satisfies all 3 tx.run calls
        return {"c": 42, "date": "2026-04-23"}
        
    mock_session.execute_read.side_effect = side_effect_execute_read
    
    mock_session_context = MagicMock()
    mock_session_context.__enter__.return_value = mock_session
    mock_driver_instance.session.return_value = mock_session_context
    mock_get_driver.return_value = mock_driver_instance
    
    # 3. Mock MongoDB Storage
    mock_mongo_instance = MagicMock()
    mock_mongo_instance.get_system_status.return_value = "OK"
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.estimated_document_count.return_value = 99
    
    # Route all db['collection'] calls to our mock_collection
    mock_db.__getitem__.return_value = mock_collection
    mock_mongo_instance.db = mock_db
    
    mock_mongo.return_value = mock_mongo_instance

    # Run the script!
    run_pulse_check()

    # Verify a log file was successfully written
    root_dir = Path(__file__).resolve().parent.parent.parent
    log_dir = root_dir / "helper_scripts" / "logs"
    
    log_files = glob.glob(str(log_dir / "pulse_status_*.log"))
    assert len(log_files) > 0, "Expected a pulse_status_*.log file to be generated, but found none."
    
    # Cleanup so we don't spam the CI environment with log files
    for f in log_files:
        os.remove(f)
