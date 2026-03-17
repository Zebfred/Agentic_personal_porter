import sys
import json
import os
from datetime import datetime
from pathlib import Path

# Path resolution to ensure we can reach database modules
root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.database.mongo_storage import SovereignMongoStorage

def sample_mongo_data(limit=5):
    """
    Pulls a sample of documents from the Raw and Formatted MongoDB collections
    to inspect their shape and data structure, dumping them to the specified directory.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = root / "data" / "google_calendar" / "Mongo_sample"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"--- 🔍 Sampling MongoDB Collections (Limit: {limit}) ---")
    
    storage = SovereignMongoStorage()
    
    # Fetch Raw Samples
    print("\n--- 📦 RAW COLLECTION (Landing Zone) ---")
    raw_samples = list(storage.raw_col.find().limit(limit))
    if not raw_samples:
        print("⚠️ No raw events found.")
    else:
        raw_file = out_dir / f"Gcal_raw_{date_str}.json"
        with open(raw_file, 'w') as f:
            json.dump(raw_samples, f, indent=4, default=str)
        print(f"✅ Saved {len(raw_samples)} raw events to: {raw_file}")
        
    # Fetch Formatted Samples
    print("\n--- 🎯 FORMATTED COLLECTION (Graph Ready) ---")
    formatted_samples = list(storage.formatted_col.find().limit(limit))
    if not formatted_samples:
        print("⚠️ No formatted events found.")
    else:
        fmt_file = out_dir / f"Gcal_formatted_{date_str}.json"
        with open(fmt_file, 'w') as f:
            json.dump(formatted_samples, f, indent=4, default=str)
        print(f"✅ Saved {len(formatted_samples)} formatted events to: {fmt_file}")

if __name__ == "__main__":
    # You can change the limit here if you want to see more examples.
    sample_mongo_data(limit=25)
