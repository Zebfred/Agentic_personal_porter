import os
import pickle
import logging
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
from .google_calendar_authentication_helper import get_calendar_credentials
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This defines what our app is allowed to do. 
# Using read-write access to enable syncing actual activities back to calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """
    Handles the OAuth 2.0 flow and returns a service object to interact with the API.
    
    Note: 
    - credentials.json should be from Google Cloud project (zebfred.nexus@gmail.com)
    - token.pickle will be created for the user account (zebfred22@gmail.com) during OAuth flow
    - Token is cached so user doesn't need to re-authenticate every time
    
    Returns:
        googleapiclient.discovery.Resource: Calendar API service object
        
    Raises:
        FileNotFoundError: If credentials.json is not found
        Exception: If OAuth flow fails
    """
    try:
        creds = get_calendar_credentials()
        service = build('calendar', 'v3', credentials=creds)
        logger.info("Calendar service initialized successfully via helper.")
        return service
    except Exception as e:
        logger.error(f"Failed to build calendar service: {e}")
        raise
    
