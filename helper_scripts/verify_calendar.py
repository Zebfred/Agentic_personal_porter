import os
import json
import calendar
import argparse
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dateutil import parser

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
DATA_DIR = os.path.join(os.getcwd(), 'data', 'google_calendar')
os.makedirs(DATA_DIR, exist_ok=True)

CATEGORY_MAPPING = {
    "keywords": {
        "Professional-core": ["dev", "work", "engineer", "data", "deep dive", "development", "working on lauirl"],
        "Professional-extended": ["meeting", "sync", "interview", "client"],
        "Relationship": ["fellowship", "relationship", "anu", "date", "call with", "family", "dog"],
        "Self-Care": ["gym", "workout", "meditation", "praying", "thinking", "health", "call"],
        "Maintenance": ["laundry", "clean", "grocery", "admin", "setup", "laptop", "haircut", "waking", "getting started", "zeb's intended sleep time", "lunch"],
        "Hero's Work": ["project", "porter", "lauirl", "theory", "planning"],
        "Survival": ["jury duty", "bills", "doctor", "therapy", "pharmacy", "vet", "appointment", "travel", "commute"],
        "Restorive": ["calling it quit","sleep", "girlfriend", "nap", "relax", "rest", "reading", "tv", "show", "movie", "game", "gaming", "fun" , "party" , "hangout"],
        "Uncategorized": []
    },
    "colors": {
        "6": "Professional-core",
        "10":"Professional-extended",
        "11": "Survival",
        "2":  "Self-Care",
        "5":  "Relationship",
        "3":  "Maintenance",
        "8":  "Restorive",
        "7":  "Hero's Work"
    }
}

# --- Core Logic ---

def get_calendar_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def get_time_range(mode):
    """Calculates timeMin and timeMax based on the requested mode."""
    now = datetime.now(timezone.utc)
    
    if mode == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif mode == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        _, last_day_num = calendar.monthrange(now.year, now.month)
        end_date = now.replace(day=last_day_num, hour=23, minute=59, second=59, microsecond=0)
    else:
        raise ValueError("Invalid mode. Use 'day' or 'month'.")

    return start_date.isoformat().replace('+00:00', 'Z'), end_date.isoformat().replace('+00:00', 'Z')

def get_time_chunk(hour):
    if 5 <= hour < 9: return "Early Morning"
    if 9 <= hour < 12: return "Late Morning"
    if 12 <= hour < 14: return "Midday"
    if 14 <= hour < 17: return "Afternoon"
    if 17 <= hour < 21: return "Evening"
    return "Night"

def determine_category(title, color_id):
    if color_id in CATEGORY_MAPPING["colors"]:
        return CATEGORY_MAPPING["colors"][color_id]
    
    title_lower = title.lower()
    for pillar, keywords in CATEGORY_MAPPING["keywords"].items():
        if any(kw in title_lower for kw in keywords):
            return pillar
    return "Uncategorized"

def parse_calendar_to_intentions(raw_events):
    formatted_intentions = []
    for event in raw_events:
        if 'dateTime' not in event.get('start', {}):
            continue

        start_dt = parser.parse(event['start']['dateTime'])
        end_dt = parser.parse(event['end']['dateTime'])
        duration_minutes = (end_dt - start_dt).total_seconds() / 60

        category_label = determine_category(event.get('summary', ''), event.get('colorId', 'Default'))
       
        intention = {
            "source_id": event['id'],
            "title": event.get('summary', 'Untitled Event'),
            "context_notes": event.get('description', ''),
            "timing": {
                "start_iso": start_dt.isoformat(),
                "end_iso": end_dt.isoformat(),
                "duration_minutes": int(duration_minutes),
                "time_chunk": get_time_chunk(start_dt.hour)
            },
            "meta": {
                "label": category_label,
                "google_color_id": event.get('colorId', 'Default'),
                "is_processed": False
            }
        }
        formatted_intentions.append(intention)
    return formatted_intentions

def main():
    arg_parser = argparse.ArgumentParser(description="Fetch Google Calendar data for a day or a month.")
    arg_parser.add_argument("--mode", choices=["day", "month"], default="day", help="Time range to fetch.")
    args = arg_parser.parse_args()

    print(f"🚀 Starting Calendar Fetch ({args.mode} mode)...")
    service = get_calendar_service()

    time_min, time_max = get_time_range(args.mode)
    print(f"📅 Fetching: {time_min} to {time_max}")

    events_result = service.events().list(
        calendarId='primary', 
        timeMin=time_min, 
        timeMax=time_max,
        singleEvents=True, 
        orderBy='startTime',
        maxResults=2500
    ).execute()
    
    raw_events = events_result.get('items', [])
    clean_data = parse_calendar_to_intentions(raw_events)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_prefix = f"{args.mode}_{timestamp}"
    
    raw_path = os.path.join(DATA_DIR, f"{file_prefix}_raw.json")
    fmt_path = os.path.join(DATA_DIR, f"{file_prefix}_formatted.json")

    with open(raw_path, 'w') as f:
        json.dump(raw_events, f, indent=2)
    with open(fmt_path, 'w') as f:
        json.dump(clean_data, f, indent=2)

    print(f"✅ Success! Found {len(raw_events)} events.")
    print(f"📁 Files saved: {file_prefix}_raw.json and {file_prefix}_formatted.json")

if __name__ == '__main__':
    main()