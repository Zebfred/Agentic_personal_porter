import os
import json
import calendar
from datetime import datetime
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
    """Authenticates and returns the Google Calendar Service."""
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

def get_month_range():
    """Returns ISO strings for the start and end of the current month."""
    now = datetime.utcnow()
    
    # First day of the month
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Last day of the month
    _, last_day_num = calendar.monthrange(now.year, now.month)
    end_date = now.replace(day=last_day_num, hour=23, minute=59, second=59, microsecond=0)
    
    # Format for Google API (RFC3339)
    return start_date.isoformat() + 'Z', end_date.isoformat() + 'Z'

# --- THE LIFE PILLAR MAP ---
# This is the "Learning" base. We map keywords and Google Colors to Pillars.
# Google Color IDs: 1 (Blue/Lavender), 2 (Green/Sage), 10 (Green/Basil), 11 (Red/Tomato), etc.
CATEGORY_MAPPING = {
    "keywords": {
        "Professional-core": ["dev", "work", "engineer", "data", "Deep Dive", "development", "Working on LaUIrl",],
        "Professional-extended": ["meeting", "sync", "interview", "client"],
        "Relationship": ["fellowship", "relationship", "anu", "date", "call with", "family", "dog"],
        "Self-Care": ["gym", "workout", "meditation", "praying", "thinking", "health", "call"],
        "Maintenance": ["laundry", "clean", "grocery", "admin", "setup", "laptop", "haircut", "waking", "Getting started", "Zeb's intended Sleep Time", "lunch"],
        "Hero's Work": ["project", "porter", "lauirl", "theory", "planning"],
        "Survival": ["jury duty", "bills", "doctor", "therapy", "pharmacy", "vet", "appointment", "travel", "commute"],
        "Restorive": ["Calling it quit","sleep", "girlfriend", "nap", "relax", "rest", "reading", "tv", "show", "movie", "game", "gaming", "fun" , 	"party" , 	"hangout"],
        "Uncategorized": []
    },
    "colors": {
        "6": "Professional-core", # Tangerine (Orange)
        "10":"Professional-extended", # Banana (Yellow)
        "11": "Survival",     # Tomato (Red)
        "2":  "Self-Care",    # Sage (Green)
        "5":  "Relationship", # Basil (Dark Green)
        "3":  "Maintenance",  # Grape (Purple)
        "8":  "Restorive",    # Gray (Gray)
        "7":  "Hero's Work"   # Peacock (Blue)
    }
}

def get_time_chunk(hour):
    if 5 <= hour < 9: return "Early Morning"
    if 9 <= hour < 12: return "Late Morning"
    if 12 <= hour < 14: return "Midday"
    if 14 <= hour < 17: return "Afternoon"
    if 17 <= hour < 21: return "Evening"
    return "Night"

def determine_category(title, color_id):
    """
    Heuristic to guess the life pillar. 
    Prioritizes Color ID, then falls back to Keyword matching.
    """
    # 1. Check Color ID First (Explicit intent)
    if color_id in CATEGORY_MAPPING["colors"]:
        return CATEGORY_MAPPING["colors"][color_id]
    
    # 2. Check Keywords in Title
    title_lower = title.lower()
    for pillar, keywords in CATEGORY_MAPPING["keywords"].items():
        if any(kw in title_lower for kw in keywords):
            return pillar
            
    return "Uncategorized"

def parse_calendar_to_intentions(raw_events):
    """
    Transforms raw Google Calendar noise into clean Agentic Intentions.
    """
    formatted_intentions = []

    for event in raw_events:
        # 1. Skip all-day events (usually holidays/birthdays) if they have no time
        if 'dateTime' not in event.get('start', {}):
            continue

        # 2. Extract Timing
        start_dt = parser.parse(event['start']['dateTime'])
        end_dt = parser.parse(event['end']['dateTime'])
        duration_minutes = (end_dt - start_dt).total_seconds() / 60

        # 3. Extract Context (The "Agentic" Meat)
        # Google description often contains Zoom links etc. We want the text.
        raw_title = event.get('summary', 'Untitled Event')
        raw_desc = event.get('description', '')
        color_id = event.get('colorId', 'Default')
        
        # 4. Determine "Category Hint" (Maslow Tier guess)
        # This is where we can map Color IDs later. For now, default to General.
        #Determine the Pillar (Label)
        category_label = determine_category(raw_title, color_id)
       
                # 5. Build the Golden Object
        intention = {
            "source_id": event['id'],
            "title": raw_title,
            "context_notes": raw_desc,
            "timing": {
                "start_iso": start_dt.isoformat(),
                "end_iso": end_dt.isoformat(),
                "duration_minutes": int(duration_minutes),
                "time_chunk": get_time_chunk(start_dt.hour)
            },
            "meta": {
                "label": category_label, # The "Personal" learning hook
                "google_color_id": color_id,
                "is_processed": False # Flag for the Learning Agent to refine later
            }
        }
        formatted_intentions.append(intention)

    return formatted_intentions

def main():
    print("🚀 Starting Monthly Calendar Fetch...")
    service = get_calendar_service()

    # Get dynamic time range
    time_min, time_max = get_month_range()
    print(f"📅 Fetching events from {time_min} to {time_max}...")

    # Fetch Events
    events_result = service.events().list(
        calendarId='primary', 
        timeMin=time_min, 
        timeMax=time_max,
        singleEvents=True, 
        orderBy='startTime',
        maxResults=2500 # Ensure we get everything
    ).execute()
    
    raw_events = events_result.get('items', [])
    clean_data = parse_calendar_to_intentions(raw_events)
    
    # Save Artifacts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = os.path.join(DATA_DIR, f"month_raw_{timestamp}.json")
    fmt_path = os.path.join(DATA_DIR, f"month_formatted_{timestamp}.json")

    with open(raw_path, 'w') as f:
        json.dump(raw_events, f, indent=2)
    with open(fmt_path, 'w') as f:
        json.dump(clean_data, f, indent=2)

    print(f"✅ Success! Found {len(raw_events)} events for this month.")
    print(f"📁 Raw data: {raw_path}")
    print(f"✨ Formatted data: {fmt_path}")

if __name__ == '__main__':
    main()