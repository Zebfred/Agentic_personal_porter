import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# This defines what our app is allowed to do. We're asking for read-only access.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_PICKLE_FILE = 'token.pickle'
API_BASE_URL = 'http://127.0.0.1:5000'

def get_calendar_service():
    """
    Handles the OAuth 2.0 flow and returns a service object to interact with the API.
    It cleverly caches your credentials in a 'token.pickle' file so you don't have
    to log in every single time you start the server. It's like a bouncer
    who remembers your face after you show your ID once.
    """
    creds = None
    # Check if we have a saved token (a hall pass from a previous login)
    if os.path.exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If there's no valid token, we need to get a new one.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # If the hall pass is expired, we can refresh it without bothering the user.
            creds.refresh(Request())
        else:
            #desktop app:
            #flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            #creds = flow.run_local_server(port=0) # port=0 will automatically find an available port
            
            #web app:
            #Initial flow to get credentials, but I believe this needs to be done in a route handler.(No? haha)
            # Maybe, but I going to have to dig into it as it relates back to cloud project setup.
            # This is the one-time-only process where you have to grant permission.
            # It will print a URL in your Flask terminal. You must copy/paste it into your browser.
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # We use run_console() because our web server isn't a traditional desktop app.
            creds = flow.run_local_server()


            # Assuming you have a redirect_uri configured in your Google Cloud Project and it matches the one used here.
            #Think I still have to set that up...
            flow.redirect_uri = API_BASE_URL + '/oauth2callback' 

            authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
            print("Please go to this URL to authorize the application:", authorization_url)

            # Redirect the user to authorization_url in their browser
            # # After authorization, Google will redirect to YOUR_REDIRECT_URI with a code
            # # Then, you can exchange the code for credentials:
            # # creds = flow.fetch_token(code=request.args['code'])


           

        # Save the new, shiny token for next time.
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)

    # Build the service object that can actually make API calls.
    service = build('calendar', 'v3', credentials=creds)
    return service
