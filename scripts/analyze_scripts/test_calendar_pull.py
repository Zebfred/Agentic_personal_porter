from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import json

# Path resolution

from src.database.calendar_raw_sync_to_mongo import SovereignCalendarSync
from src.database.mongo_storage import SovereignMongoStorage

def main():
    logger.info("=== Starting Calendar Pull Test ===")
    
    storage = SovereignMongoStorage()
    cal_sync = SovereignCalendarSync()
    
    # Get the first opted-in user, preferring personal gmail
    users = storage.get_sync_opted_in_users()
    if not users:
        logger.info("No users opted in. Cannot test pull.")
        return
        
    user = next((u for u in users if "gmail.com" in u.get("email", "")), users[0])
    user_email = user.get("email")
    refresh_token = user.get("google_refresh_token")
    
    if not refresh_token:
        logger.info(f"User {user_email} has no refresh token.")
        return
        
    logger.info(f"Testing pulls for user: {user_email}")
    
    # Test 1: Sliding Window
    logger.info("\n--- Test 1: Sliding Window ---")
    try:
        ops_count_sliding = cal_sync.pull_sliding_window(user_email=user_email, refresh_token=refresh_token)
        logger.info(f"✅ Sliding window pulled {ops_count_sliding} events successfully.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.info(f"❌ Sliding window pull failed: {e}")
        
    # Test 2: Historical Backlog
    logger.info("\n--- Test 2: Historical Backlog ---")
    try:
        oldest_cursor = storage.get_historical_sync_cursor(user_email)
        logger.info(f"Current oldest cursor: {oldest_cursor}")
        ops_count_historic, new_cursor = cal_sync.pull_historical_backlog(
            user_email=user_email, 
            refresh_token=refresh_token, 
            oldest_cursor=oldest_cursor
        )
        logger.info(f"✅ Historical backlog pulled {ops_count_historic} events successfully.")
        logger.info(f"New cursor would be: {new_cursor}")
        
        # Don't necessarily update the cursor if this is just a dry test, 
        # but if the user wants it to be a real test we can.
        # storage.update_historical_sync_cursor(user_email, new_cursor)
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.info(f"❌ Historical backlog pull failed: {e}")

    # Test 3: Export Sample Data
    logger.info("\n--- Test 3: Exporting Sample Data ---")
    sample_dir = root / "data" / "google_calendar"
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample_file = sample_dir / "Mongo_sample.json"
    
    # Grab 5 recent events from the raw collection
    sample_events = list(cal_sync.raw_collection.find({"user_email": user_email}).sort("_id", -1).limit(5))
    
    # Convert ObjectIds to strings for JSON serialization
    for ev in sample_events:
        if "_id" in ev:
            ev["_id"] = str(ev["_id"])
            
    with open(sample_file, "w") as f:
        json.dump(sample_events, f, indent=2)
        
    logger.info(f"✅ Exported {len(sample_events)} sample events to {sample_file}")
    
if __name__ == "__main__":
    main()
