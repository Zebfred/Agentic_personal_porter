import os
from pathlib import Path
from dotenv import load_dotenv

def get_project_root() -> Path:
    """
    Returns the absolute path to the project root directory.
    Assumes this file is located at project_root/src/utils/path_utils.py
    """
    # .parent of utils is src, .parent of src is project_root
    return Path(__file__).resolve().parent.parent.parent

def load_env_vars():
    """
    Locates the .auth/.env file and loads it into the environment.
    """
    root = get_project_root()
    env_path = root / ".auth" / ".env"
    
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        # We'll use a print here instead of a raise so we don't 
        # crash scripts that don't actually need the .env
        print(f"⚠️ Warning: .env file not found at {env_path}")

def get_auth_file(filename: str) -> str:
    """
    Returns the absolute path to a specific file in the .auth folder.
    """
    root = get_project_root()
    return str(root / ".auth" / filename)