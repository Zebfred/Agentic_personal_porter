import os.path
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_service():
    """
    Handles OAuth2 flow for zebfred22@gmail.com.
    Requires credentials.json in the project root.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def get_today_intentions():
    """
    Fetches events from today for the primary calendar.
    """
    service = get_calendar_service()
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    end_of_day = (datetime.datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat() + 'Z'
    
    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=end_of_day,
                                        singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        return []
    
    intentions = []
    for event in events:
        intentions.append({
            'summary': event.get('summary'),
            'start': event.get('start').get('dateTime', event.get('start').get('date')),
            'description': event.get('description', '')
        })
    return intentions

if __name__ == '__main__':
    print("Verifying Calendar Connection for zebfred22@gmail.com...")
    events = get_today_intentions()
    for e in events:
        print(f"- {e['summary']} at {e['start']}")