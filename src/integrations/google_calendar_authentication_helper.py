import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# This defines what our app is allowed to do. We're asking for read-only access.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


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
        "token": os.path.join(auth_dir, 'token.pickle')
    }

def get_calendar_credentials():
    """Handles the OAuth2 flow and returns valid credentials."""
    paths = get_auth_paths()
    creds = None

    # Load existing token if it exists
    if os.path.exists(paths["token"]):
        with open(paths["token"], 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(paths["credentials"]):
                raise FileNotFoundError(
                    f"Missing credentials file at {paths['credentials']}. "
                    "Please place your Google Cloud credentials.json there."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                paths["credentials"], SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(paths["token"], 'wb') as token:
            pickle.dump(creds, token)

    return creds
