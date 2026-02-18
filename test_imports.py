import sys
import os
from pydantic import SecretStr
from dotenv import load_dotenv


# Load environment variables from .env file
# Get the base directory of your project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Construct the full path to your .env file
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)


def verify_system():
    print("🚀 Starting Project Sanitization Check...")
    
    # Verify Root Discovery
    try:
        import src.main
        print("✅ Project Root (src) is correctly in PYTHONPATH.")
    except ImportError:
        print("❌ Project Root (src) NOT found. Ensure you run from root directory.")

    # Verify Auth Helper Connectivity
    try:
        from src.integrations.google_calendar_authentication_helper import get_auth_paths
        paths = get_auth_paths()
        print(f"✅ Auth Helper located .auth at: {paths['credentials']}")
    except Exception as e:
        print(f"❌ Auth Helper Failed: {e}")

    # Verify SecretStr & Env Loading
    from pydantic import SecretStr
    from dotenv import load_dotenv
    
    # Match the main.py logic
    # Load environment variables from .env file
    # Get the base directory of your project
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Construct the full path to your .env file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    # Construct the full path to your .env file inside the .auth directory
    env_path = os.path.join(project_root, '.auth', '.env')
    load_dotenv(dotenv_path=env_path)

    
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        # Wrap in SecretStr to confirm Pylance-ready types
        secret_key = SecretStr(api_key)
        print(secret_key)
        print(f"✅ GROQ_API_KEY loaded and sanitized as SecretStr.")
    else:
        print("❌ GROQ_API_KEY missing from .auth/.env")

if __name__ == "__main__":
    verify_system()