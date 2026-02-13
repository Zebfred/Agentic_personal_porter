import os
import json
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dateutil import parser

# Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
DATA_DIR = os.path.join(os.getcwd(), 'data', 'google_calendar')
os.makedirs(DATA_DIR, exist_ok=True)

def get_calendar_service():
    creds = None
    # Look for existing token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)

def parse_calendar_to_intentions(raw_events):
    formatted_intentions = []
    for event in raw_events:
        if 'dateTime' not in event.get('start', {}):
            continue

        start_dt = parser.parse(event['start']['dateTime'])
        end_dt = parser.parse(event['end']['dateTime'])
        duration = (end_dt - start_dt).total_seconds() / 60

        formatted_intentions.append({
            "source_id": event['id'],
            "title": event.get('summary', 'Untitled'),
            "context_notes": event.get('description', ''),
            "timing": {
                "start_iso": start_dt.isoformat(),
                "duration_minutes": int(duration)
            },
            "meta": {
                "google_color_id": event.get('colorId', 'Default')
            }
        })
    return formatted_intentions

def main():
    print("🚀 Starting Calendar Data Verification...")
    service = get_calendar_service()

    # Define "Today" (Midnight to Midnight)
    now = datetime.utcnow().isoformat() + 'Z'
    end_of_day = (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'

    print(f"📅 Fetching events for the next 24 hours...")
    events_result = service.events().list(
        calendarId='primary', timeMin=now, timeMax=end_of_day,
        singleEvents=True, orderBy='startTime'
    ).execute()
    
    raw_events = events_result.get('items', [])
    
    # Process Data
    clean_data = parse_calendar_to_intentions(raw_events)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save Artifacts
    raw_path = os.path.join(DATA_DIR, f"cal_raw_{timestamp}.json")
    fmt_path = os.path.join(DATA_DIR, f"cal_formatted_{timestamp}.json")

    with open(raw_path, 'w') as f:
        json.dump(raw_events, f, indent=2)
    with open(fmt_path, 'w') as f:
        json.dump(clean_data, f, indent=2)

    print(f"✅ Success! Found {len(raw_events)} events.")
    print(f"📁 Raw data: {raw_path}")
    print(f"✨ Formatted data: {fmt_path}")

if __name__ == '__main__':
    main()