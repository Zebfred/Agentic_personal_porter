import os
import sys
from pathlib import Path

# Setup path so we can import from src
root = Path(__file__).resolve().parent.parent
sys.path.append(str(root))

from src.utils.path_utils import load_env_vars
from src.database.mongo_storage import SovereignMongoStorage

def main():
    load_env_vars()
    print("--- MongoDB Collections Overview ---")
    
    try:
        storage = SovereignMongoStorage()
        db = storage.db
        
        collections = db.list_collection_names()
        print(f"{'Collection Name':<35} | {'Document Count':<15} | {'Last Update / Record Time':<30}")
        print("-" * 85)
        
        for coll_name in sorted(collections):
            coll = db[coll_name]
            # Use estimated_document_count for speed on large collections
            count = coll.estimated_document_count()
            
            # To get an idea of last update, we'll pull the most recently inserted/updated doc
            # We sort by natural order or _id descending
            latest_doc = coll.find_one({}, sort=[('_id', -1)])
            
            last_updated = "Unknown"
            if count == 0:
                last_updated = "N/A (Empty)"
            elif latest_doc:
                # Try common timestamp fields that we use in our data models
                for ts_field in ['porter_ingested_at', 'timestamp', 'updated_at', 'created_at', 'start']:
                    if ts_field in latest_doc:
                        # Some timestamps are nested (like start.dateTime from google)
                        val = latest_doc[ts_field]
                        if isinstance(val, dict) and 'dateTime' in val:
                            last_updated = str(val['dateTime'])
                        else:
                            last_updated = str(val)
                        break
                
                # Fallback to ObjectId generation time if it's a standard Mongo _id
                if last_updated == "Unknown" and hasattr(latest_doc['_id'], 'generation_time'):
                    last_updated = str(latest_doc['_id'].generation_time)
                
            print(f"{coll_name:<35} | {count:<15} | {str(last_updated)[:30]:<30}")
            
    except Exception as e:
        print(f"Error accessing MongoDB: {e}")

if __name__ == "__main__":
    main()
