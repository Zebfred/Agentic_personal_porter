#!/usr/bin/env python3
import logging
from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os
import requests
import json
import sys
from datetime import datetime

def main():
    # Attempt to load from .auth/.env
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.auth', '.env')
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        # Fallback to manual parsing if python-dotenv is not installed
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

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.info("Error: GROQ_API_KEY environment variable is not set.")
        logger.info("Please set it using: export GROQ_API_KEY='your_api_key'")
        sys.exit(1)

    url = "https://api.groq.com/openai/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    logger.info("Fetching available models from Groq API...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        models = data.get("data", [])
        
        logger.info("\n=== Available Groq Models ===")
        logger.info(f"{'Model ID':<35} | {'Owned By':<15} | {'Created'}")
        logger.info("-" * 75)
        
        # Sort models alphabetically by ID
        models.sort(key=lambda x: x.get("id", ""))
        
        for model in models:
            model_id = model.get("id", "Unknown")
            owned_by = model.get("owned_by", "Unknown")
            created_ts = model.get("created", 0)
            
            # Convert timestamp to readable date if valid
            try:
                created_date = datetime.fromtimestamp(created_ts).strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                created_date = str(created_ts)
                
            logger.info(f"{model_id:<35} | {owned_by:<15} | {created_date}")
            
        logger.info("-" * 75)
        logger.info(f"Total models found: {len(models)}")
            
    except requests.exceptions.RequestException as e:
        logger.info(f"Error connecting to Groq API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.info(f"Status Code: {e.response.status_code}")
            try:
                error_data = e.response.json()
                logger.info(f"Response: {json.dumps(error_data, indent=2)}")
            except json.JSONDecodeError:
                logger.info(f"Response: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
