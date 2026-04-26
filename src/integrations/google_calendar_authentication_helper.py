import os
from pathlib import Path
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# This defines what our app is allowed to do. Defaulting to full calendar access for syncing.
SCOPES = ['https://www.googleapis.com/auth/calendar']

root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))


def get_auth_paths():
    """
    Dynamically finds the project root and returns paths for auth files.
    Assumes this file is in project_root/src/integrations/
    """
    # Move up three levels: integrations -> src -> project_root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    auth_dir = os.path.join(project_root, '.auth')
    
    # Ensure the .auth directory exists
    if not os.path.exists(auth_dir):
        os.makedirs(auth_dir)
        
    return {
        "credentials": os.path.join(auth_dir, 'credentials.json'),
        "token": os.path.join(auth_dir, 'token.json')
    }

def get_calendar_credentials(scopes=None):
    """Handles the OAuth2 flow and returns valid credentials."""
    paths = get_auth_paths()
    creds = None
    target_scopes = scopes if scopes else SCOPES

    # Load existing token if it exists
    if os.path.exists(paths["token"]):
        try:
            creds = Credentials.from_authorized_user_file(paths["token"], target_scopes)
        except Exception:
            # If the token file is invalid or corrupted, we'll re-authenticate
            creds = None

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # If refresh fails, set creds to None to trigger a fresh login flow below
                creds = None

        if not creds or not creds.valid:
            if not os.path.exists(paths["credentials"]):
                raise FileNotFoundError(
                    f"Missing credentials file at {paths['credentials']}. "
                    "Please place your Google Cloud credentials.json there."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                paths["credentials"], target_scopes
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(paths["token"], 'w') as token:
            token.write(creds.to_json())

    return creds

def get_calendar_credentials_for_user(refresh_token: str, scopes=None):
    """
    Creates valid Google OAuth Credentials using a refresh token from the database.
    Requires the global client_id and client_secret to refresh the token.
    """
    import json
    paths = get_auth_paths()
    target_scopes = scopes if scopes else SCOPES
    
    if not os.path.exists(paths["credentials"]):
        raise FileNotFoundError(
            f"Missing credentials file at {paths['credentials']}. "
            "Cannot refresh user token without client secrets."
        )
        
    with open(paths["credentials"], 'r') as f:
        client_config = json.load(f)
        
    # Handle both 'web' and 'installed' types of credentials.json
    client_info = client_config.get('web') or client_config.get('installed')
    if not client_info:
        raise ValueError("Invalid credentials.json format")
        
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=client_info.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=client_info.get('client_id'),
        client_secret=client_info.get('client_secret'),
        scopes=target_scopes
    )
    
    # Force a refresh to get an access token
    creds.refresh(Request())
    return creds
