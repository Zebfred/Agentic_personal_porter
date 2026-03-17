import os
from pathlib import Path

# Find root
root_dir = Path(__file__).resolve().parent.parent

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