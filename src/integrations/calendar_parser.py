import json
import os
import sys
from pathlib import Path
from datetime import datetime
from dateutil import parser # pip install python-dateutil

root = Path(__file__).resolve().parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

# Define your storage paths
DATA_DIR = os.path.join(os.getcwd(), 'data', 'google_calendar')
os.makedirs(DATA_DIR, exist_ok=True)

# --- THE LIFE PILLAR MAP ---
# This is the "Learning" base. We map keywords and Google Colors to Pillars.
ACTUAL_CATEGORY_MAPPING = {
    "intent_to_actual_mapping": {
        "Career Goal": "Career related", 
        "Health Goal": "Health related", 
        "Loved ones": "Loved Ones", 
        "Leisure Goal": "Leisures_related",
        "Interest Goal": "Interests_related", 
        "Spiritual Goal": "Spiritual_related", 
        "Social Goal": "Social_related", 
        "Mundane Goal": "Chore_related",
        "Detriments to Avoid": "Detriments_related"
    },
    "actual_categorization_with_keywords": {        
        "Career related": {
            "Professional-core": ["dev", "work", "engineer", "data", "deep dive", "development", "working on lauirl"],
            "Professional-extended": ["meeting", "sync", "interview", "client", "planning"],
            "Hero's Work": ["project", "porter", "lauirl", "theory", "engineering"]
        },
        "Health related": {
            "Exercise": ["workout", "exercise", "gym"],
            "Diet": ["lunch", "dinner", "breakfast", "food"],
            "Sleep": ["sleep", "nap"]
        },
        "Loved Ones": {
            "Romantic_related": ["relationship", "anu", "date", "call with"],
            "Family_related": ["family", "mom"],
            "Pet_related": ["pet", "doggy", "dog", "puppy", "walk with dogs"]
        },
        "Leisures_related": {
            "General": ["relaxing", "calling it quits", "movie", "hanging out", "board games", "hiking with dogs"]
        },
        "Interests_related": {
            "General": ["hobbies", "reading", "activities", "caving", "exploring","nature", "museum", "drawing" ]
        },
        "Spiritual_related": {
            "General": ["meditate", "pray", "higher power", "religious", "church"]
        },
        "Social_related": {
            "General": ["fellowship", "friends", "social", "amiable with strangers", "be available to friends and family"]
        },
        "Chore_related": {
            "General": ["laundry", "clean", "grocery", "admin", "setup", "haircut", "waking", "getting started", "jury duty", "bills", "doctor", "therapy", "pharmacy", "vet", "appointment", "travel", "commute"]
        },
        "Detriments_related": {
            "General": ["procrastinate", "ineffective work", "mindlessly engaged", "acting in selfwill/fear"]
        },
        "Uncategorized": {
            "General": []
        }
    },
    "colors": {
        "1": "Uncategorized",                 # Lavender (Default)
        "2": "Social_related",                # Sage
        "3": "Loved Ones",                    # Grape
        "5": "Chore_related",                 # Banana
        "6": ("Career related", "Professional-extended"),  # Tangerine
        "7": ("Career related", "Hero's Work"),            # Peacock
        "8": ["Health related", "Spiritual_related"],      # Graphite (Shared!)
        "9": ("Career related", "Professional-core"),      # Blueberry
        "10": "Leisures_related",             # Basil
        "11": "Detriments_related",           # Tomato
        "default": "Uncategorized"
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
    Heuristic to guess the life pillar and subcategory.
    Returns a dict with 'pillar' and 'subcategory'.
    """
    title_lower = title.lower()
    color_match = ACTUAL_CATEGORY_MAPPING["colors"].get(str(color_id))

    # 1. Explicit Color Checking
    if color_match:
        if isinstance(color_match, tuple):
            # Perfect exact match for a subcategory (e.g., Tangerine -> Prof-extended)
            return {"pillar": color_match[0], "subcategory": color_match[1]}
        
        elif isinstance(color_match, str) and color_match != "Uncategorized":
            # Direct match to a single pillar
            return {"pillar": color_match, "subcategory": "General"}
        
        # If it's a list (like Graphite [Health, Spiritual]), we skip returning here 
        # and let the keyword logic below break the tie!

    # 2. Keyword Fallback & Tie-Breaker
    for pillar, subcategories in ACTUAL_CATEGORY_MAPPING["actual_categorization_with_keywords"].items():
        # If we have a shared color list, only search within those specific pillars to save time
        if isinstance(color_match, list) and pillar not in color_match:
            continue
            
        for subcat, keywords in subcategories.items():
            if any(kw.lower() in title_lower for kw in keywords):
                return {"pillar": pillar, "subcategory": subcat}
                
    return {"pillar": "Uncategorized", "subcategory": "General"}

def event_record_type(event):
    """
    Compares the event's last modified time with its start time to 
    determine if it's a pre-planned 'Intention' or a logged 'Actual'.
    """
    try:
        start_str = event['start'].get('dateTime')
        updated_str = event.get('updated') # The time the event was last modified
        
        if not start_str or not updated_str:
            return "Intention" # Default safely

        start_dt = parser.parse(start_str)
        updated_dt = parser.parse(updated_str)
        
        # If the event was created/modified after the start time, it's an actual log
        if updated_dt >= start_dt:
            return "Actual"
        else:
            return "Intention"
            
    except Exception:
        return "Unknown"

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

        # Determine the Pillar and Subcategory dict
        category_data = determine_category(raw_title, color_id)
        
        # Determine if this was planned or actually done
        record_type = event_record_type(event)
       
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
                "pillar": category_data["pillar"],
                "subcategory": category_data["subcategory"],
                "record_type": record_type, # 'Actual' or 'Intention'
                "google_color_id": color_id,
                "is_processed": False
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