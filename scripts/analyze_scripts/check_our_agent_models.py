#!/usr/bin/env python3
from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os
import re
import requests
import sys

def get_groq_api_key():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.auth', '.env')
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"\'')
                        if k not in os.environ:
                            os.environ[k] = v
    return os.environ.get("GROQ_API_KEY")

def get_configured_models():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_dir = os.path.join(project_root, "src", "agents")

    models_used = {}

    # Regex to find model="model-name" or model='model-name'
    pattern = re.compile(r'model=["\']([^"\']+)["\']')

    for root, _, files in os.walk(agents_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = pattern.findall(content)
                for match in matches:
                    if match not in models_used:
                        models_used[match] = []
                    if file not in models_used[match]:
                        models_used[match].append(file)

    return models_used

def get_available_groq_models(api_key):
    url = "https://api.groq.com/openai/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return [m.get("id") for m in data.get("data", [])]
    except Exception as e:
        logger.info(f"Error fetching models from Groq: {e}")
        return []

def main():
    api_key = get_groq_api_key()
    if not api_key:
        logger.info("Error: GROQ_API_KEY not found in environment or .auth/.env")
        sys.exit(1)

    logger.info("Fetching available models from Groq...")
    available_models = get_available_groq_models(api_key)

    if not available_models:
        logger.info("Could not retrieve models from Groq. Check your API key.")
        sys.exit(1)

    logger.info("Scanning src/agents/ for configured models...")
    configured_models = get_configured_models()

    if not configured_models:
        logger.info("No models found configured in src/agents/")
        sys.exit(0)

    logger.info("\n=== Agent Models Connectivity Check ===")
    logger.info(f"{'Status':<12} | {'Model Name':<30} | {'Used In'}")
    logger.info("-" * 75)

    for model, files in sorted(configured_models.items()):
        status = "✅ OK" if model in available_models else "❌ NOT FOUND"
        files_str = ", ".join(files)
        logger.info(f"{status:<12} | {model:<30} | {files_str}")

    logger.info("-" * 75)

if __name__ == "__main__":
    main()
