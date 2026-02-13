import os
import pickle
import logging
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This defines what our app is allowed to do. 
# Using read-write access to enable syncing actual activities back to calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_PICKLE_FILE = 'token.pickle'

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
    # Check if credentials file exists
    if not os.path.exists(CREDENTIALS_FILE):
        error_msg = f"credentials.json not found at {Path(CREDENTIALS_FILE).absolute()}"
        logger.error(error_msg)
        logger.error("Please download OAuth 2.0 credentials from Google Cloud Console")
        logger.error("Project should be set up with zebfred.nexus@gmail.com")
        raise FileNotFoundError(error_msg)
    
    creds = None
    
    # Check if we have a saved token (from previous authentication)
    if os.path.exists(TOKEN_PICKLE_FILE):
        try:
            with open(TOKEN_PICKLE_FILE, 'rb') as token:
                creds = pickle.load(token)
            logger.info("Loaded existing token from token.pickle")
        except Exception as e:
            logger.warning(f"Error loading token.pickle: {e}")
            creds = None

    # If there's no valid token, we need to get a new one
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                # Try to refresh the expired token
                logger.info("Token expired, attempting to refresh...")
                creds.refresh(Request())
                logger.info("Token refreshed successfully")
            except RefreshError as e:
                logger.warning(f"Token refresh failed: {e}")
                logger.info("Will need to re-authenticate")
                creds = None
        
        if not creds:
            # This is the one-time-only process where user grants permission
            logger.info("="*60)
            logger.info("GOOGLE CALENDAR AUTHENTICATION REQUIRED")
            logger.info("="*60)
            logger.info("You will be prompted to authorize this application.")
            logger.info("Please use your zebfred22@gmail.com account when prompted.")
            logger.info("="*60)
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                # run_console() will print a URL that user must visit
                creds = flow.run_console()
                logger.info("Authentication successful!")
            except Exception as e:
                logger.error(f"OAuth flow failed: {e}")
                raise

        # Save the token for next time
        try:
            with open(TOKEN_PICKLE_FILE, 'wb') as token:
                pickle.dump(creds, token)
            logger.info(f"Token saved to {TOKEN_PICKLE_FILE}")
        except Exception as e:
            logger.warning(f"Could not save token: {e}")

    # Build the service object that can make API calls
    try:
        service = build('calendar', 'v3', credentials=creds)
        logger.info("Calendar service initialized successfully")
        return service
    except Exception as e:
        logger.error(f"Failed to build calendar service: {e}")
        raise
