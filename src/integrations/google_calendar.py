import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

root = Path(__file__).resolve().parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from src.integrations.google_calendar_authentication_helper import get_calendar_credentials

# Load environment variables from the correct .env path
load_dotenv(root / ".auth" / ".env")

# This defines what our app is allowed to do. 
# Using read-write access to enable syncing actual activities back to calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """
    Handles the OAuth 2.0 flow and returns a service object to interact with the API.
    
    Note: 
    - credentials.json should be from the Google Cloud project (see .auth/ directory)
    - token.json will be created for the authenticated user account during OAuth flow
    - Token is cached so user doesn't need to re-authenticate every time
    
    Returns:
        googleapiclient.discovery.Resource: Calendar API service object
        
    Raises:
        FileNotFoundError: If credentials.json is not found
        Exception: If OAuth flow fails
    """
    try:
        creds = get_calendar_credentials(scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        logger.info("Calendar service initialized successfully via helper.")
        return service
    except Exception as e:
        logger.error(f"Failed to build calendar service: {e}")
        raise
    
