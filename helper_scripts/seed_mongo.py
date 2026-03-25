import os
import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.mongo_storage import SovereignMongoStorage

def seed_mongo():
    print("Initiating MongoDB Artifact Seeding...")
    try:
        ms = SovereignMongoStorage()
        print(f"Connected to DB: {ms.db.name}")
        
        artifacts_to_seed = ['hero_ambition.json', 'hero_origin.json']
        
        for art in artifacts_to_seed:
            path = os.path.join('data', 'hero_artifacts', art)
            if not os.path.exists(path):
                print(f"File not found: {path}")
                continue
                
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            print(f"Loaded {art}, attempting to save to MongoDB...")
            ms.save_hero_artifact(art, data)
            print(f"Successfully saved {art} to MongoDB!")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    seed_mongo()
