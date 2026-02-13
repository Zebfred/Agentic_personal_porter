import json
import os
from datetime import datetime
from dateutil import parser # pip install python-dateutil

# Define your storage paths
DATA_DIR = os.path.join(os.getcwd(), 'data', 'google_calendar')
os.makedirs(DATA_DIR, exist_ok=True)

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

def save_debug_artifacts(raw_data, formatted_data):
    """Saves files to data/google_calendar for manual inspection."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Save RAW (The Ground Truth)
    raw_path = os.path.join(DATA_DIR, f"cal_raw_{timestamp}.json")
    with open(raw_path, 'w') as f:
        json.dump(raw_data, f, indent=2)
    print(f"✅ Saved RAW data to: {raw_path}")

    # 2. Save FORMATTED (The Agentic View)
    fmt_path = os.path.join(DATA_DIR, f"cal_formatted_{timestamp}.json")
    with open(fmt_path, 'w') as f:
        json.dump(formatted_data, f, indent=2)
    print(f"✅ Saved FORMATTED data to: {fmt_path}")

# --- USAGE EXAMPLE (Put this in your main execution flow) ---
# events = service.events().list(...).execute()
# raw_items = events.get('items', [])
# clean_items = parse_calendar_to_intentions(raw_items)
# save_debug_artifacts(raw_items, clean_items)