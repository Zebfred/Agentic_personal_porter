import os
import sys
import json
from pymongo import MongoClient, UpdateOne
from datetime import datetime, timezone, UTC
from pathlib import Path
    
# Ensure we can import from the src directory when running from helper_scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.config import MongoConfig
#from src.constants import ACTUAL_CATEGORY_MAPPING
from src.integrations.calendar_parser import parse_single_event 

# --- Mongo Setup ---

class SovereignMongoStorage:
    """
    Modern Mach 2 Storage Handler.
    Manages the transition from 'Raw' to 'Formatted' collections.
    This ensures the 'Raw Noise' of GCal is preserved while 'Formatted Signal'
    is prepared for the Neo4j Identity Graph.
    """
    def __init__(self) -> None:
        self.client = MongoClient(MongoConfig.MONGO_URI)
        self.db = self.client[MongoConfig.DB_NAME]
        self.mongo_uri = MongoConfig.MONGO_URI
        
        # Collection Pointers
        self.raw_col = self.db[MongoConfig.RAW_COLLECTION]
        self.formatted_col = self.db[MongoConfig.FORMATTED_COLLECTION]
        self.journal_col = self.db['journal_entries']
        self.artifacts_col = self.db['hero_artifacts']
        self.reflections_col = self.db['agent_reflections']
        self.system_status_col = self.db['system_status']
        self.users_col = self.db['users']
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create compound indexes to speed up multi-tenant queries."""
        from pymongo import ASCENDING
        
        # In the Timeseries (raw events), index on email + start time for quick window querying
        self.raw_col.create_index([("metadata.user_email", ASCENDING), ("start_time", ASCENDING)])
        
        # In formatted collections, index on email + start time
        self.formatted_col.create_index([("user_email", ASCENDING), ("start.dateTime", ASCENDING)])
        
        # Intent and Actual collections for quick queries
        self.db['calendar_intent_events'].create_index([("user_id", ASCENDING), ("time_slot.start", ASCENDING)])
        self.db['calendar_actual_events'].create_index([("user_id", ASCENDING), ("time_slot.start", ASCENDING)])
        self.db['calendar_unified_events'].create_index([("user_id", ASCENDING), ("time_slot.start", ASCENDING)])


    def save_journal_entry(self, log_data: dict, user_id: str = "Hero"):
        """
        Saves a direct Journal Entry into MongoDB using a nested monthly structure.
        """
        day_str = log_data.get("day") # Expected format: "YYYY-MM-DD"
        time_chunk = log_data.get("timeChunk")
        
        if not day_str or not time_chunk:
            result = self.journal_col.insert_one(log_data)
            return str(result.inserted_id)
            
        try:
            # Parse ISO Date
            dt = datetime.strptime(day_str, "%Y-%m-%d")
            month_id = dt.strftime("%Y-%m")
            
            # Get ISO week number formatted as Wxx
            iso_year, iso_week, iso_weekday = dt.isocalendar()
            week_id = f"W{iso_week:02d}"
            
            # Prepare chunk data
            chunk_data = {k: v for k, v in log_data.items() if k not in ["day", "timeChunk"]}
            chunk_data["processed_at"] = datetime.now(timezone.utc)
            
            query = {"month_id": month_id, "user_id": user_id}
            update_path = f"weeks.{week_id}.{day_str}.chunks.{time_chunk}"
            
            update = {"$set": {update_path: chunk_data}}
            
            self.journal_col.update_one(query, update, upsert=True)
            return f"Updated {month_id}"
            
        except ValueError:
            # Legacy string fallback (e.g. 'monday')
            log_data["processed_at"] = datetime.now(timezone.utc)
            result = self.journal_col.insert_one(log_data)
            return str(result.inserted_id)

    def update_journal_sync_status(self, mongo_doc_id: str, day_str: str, time_chunk: str, status_updates: dict, user_id: str = "Hero"):
        """
        Updates the sync_status of a journal entry, regardless of whether it's nested or flat.
        """
        if not day_str or not time_chunk:
            from bson.objectid import ObjectId
            try:
                self.journal_col.update_one(
                    {"_id": ObjectId(mongo_doc_id)},
                    {"$set": {f"sync_status.{k}": v for k, v in status_updates.items()}}
                )
            except Exception as e:
                print(f"Error updating flat journal entry status: {e}")
            return

        try:
            dt = datetime.strptime(day_str, "%Y-%m-%d")
            month_id = dt.strftime("%Y-%m")
            iso_year, iso_week, iso_weekday = dt.isocalendar()
            week_id = f"W{iso_week:02d}"
            
            query = {"month_id": month_id, "user_id": user_id}
            
            set_updates = {}
            for k, v in status_updates.items():
                update_path = f"weeks.{week_id}.{day_str}.chunks.{time_chunk}.sync_status.{k}"
                set_updates[update_path] = v
                
            self.journal_col.update_one(query, {"$set": set_updates})
        except ValueError:
            # Fallback for legacy
            from bson.objectid import ObjectId
            try:
                self.journal_col.update_one(
                    {"_id": ObjectId(mongo_doc_id)},
                    {"$set": {f"sync_status.{k}": v for k, v in status_updates.items()}}
                )
            except Exception as e:
                print(f"Error updating flat journal entry status: {e}")

    def get_monthly_log(self, year_month: str, user_id: str = "Hero") -> dict:
        """
        Retrieves the nested month object containing weekly journal chunks.
        year_month format: 'YYYY-MM'
        """
        doc = self.journal_col.find_one({"month_id": year_month, "user_id": user_id}, {"_id": 0})
        return doc if doc else {}

    def get_yearly_logs(self, year: str, user_id: str = "Hero") -> list:
        """
        Retrieves all nested month objects for a given year.
        year format: 'YYYY'
        """
        # Regex matching YYYY-MM
        pattern = f"^{year}-"
        cursor = self.journal_col.find({"month_id": {"$regex": pattern}, "user_id": user_id}, {"_id": 0})
        return list(cursor)

    def save_agent_reflection(self, reflection_data: dict):
        """
        Saves an AI-generated reflection into the agent_reflections collection.
        Expects keys: day, user_id, reflection_text, metadata.
        """
        reflection_data["created_at"] = datetime.now(timezone.utc)
        result = self.reflections_col.insert_one(reflection_data)
        return str(result.inserted_id)

    def get_hero_artifact(self, artifact_name: str) -> dict:
        """
        Retrieves a JSON artifact from MongoDB. Returns None if not found.
        """
        doc = self.artifacts_col.find_one({"artifact_name": artifact_name}, {"_id": 0})
        return doc.get("data") if doc else None
        
    def save_hero_artifact(self, artifact_name: str, data: dict):
        """
        Saves or updates a JSON artifact in MongoDB.
        """
        self.artifacts_col.update_one(
            {"artifact_name": artifact_name},
            {"$set": {"data": data, "updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )

    def upsert_system_status(self, key: str, value_dict: dict):
        """
        Upserts status metadata for system monitoring (e.g. for Pulse endpoint).
        """
        value_dict["updated_at"] = datetime.now(timezone.utc)
        self.system_status_col.update_one(
            {"status_key": key},
            {"$set": {"data": value_dict}},
            upsert=True
        )
        
    def get_system_status(self, key: str) -> dict:
        """
        Retrieves status metadata for a specific component.
        """
        doc = self.system_status_col.find_one({"status_key": key}, {"_id": 0})
        return doc.get("data") if doc else {}

    def get_or_create_user(self, email: str, profile_data: dict) -> dict:
        """
        Retrieves an existing user by email or provisions a new one (sign-up).
        """
        user = self.users_col.find_one({"email": email}, {"_id": 0})
        now = datetime.now(timezone.utc)
        
        if not user:
            user = {
                "email": email,
                "profile": profile_data,
                "created_at": now,
                "last_login": now,
                "guild_invite_status": "pending", # default status
                "role": "user", # Default role
                "opt_in_calendar_sync": False,
                "privacy_opt_in_analytics": False, # Explicit opt-in for admin visibility
                "google_refresh_token": None
            }
            # Special case for root admin
            nexus_admin_email = os.environ.get("NEXUS_ADMIN_EMAIL", "")
            if nexus_admin_email and email == nexus_admin_email:
                user["guild_invite_status"] = "accepted"
                
            self.users_col.insert_one(user)
        else:
            self.users_col.update_one(
                {"email": email},
                {"$set": {
                    "last_login": now,
                    "profile.name": profile_data.get("name", user.get("profile", {}).get("name")),
                    "profile.picture": profile_data.get("picture", user.get("profile", {}).get("picture"))
                }}
            )
            user["last_login"] = now
            user["profile"] = profile_data
            
        return user

    def update_user_sync_preferences(self, email: str, opt_in: bool, refresh_token: str = None):
        """
        Updates a user's calendar sync preferences and OAuth refresh token.
        """
        update_doc = {"opt_in_calendar_sync": opt_in}
        if refresh_token is not None:
            update_doc["google_refresh_token"] = refresh_token
            
        self.users_col.update_one(
            {"email": email},
            {"$set": update_doc}
        )

    def toggle_privacy_opt_in(self, email: str, opt_in: bool) -> bool:
        """
        Updates whether the user consents to sharing detailed analytics with the admin.
        """
        result = self.users_col.update_one(
            {"email": email},
            {"$set": {"privacy_opt_in_analytics": opt_in, "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    def get_sync_opted_in_users(self) -> list:
        """
        Returns a list of user profiles who have opted into background calendar sync.
        """
        return list(self.users_col.find({"opt_in_calendar_sync": True}, {"_id": 0}))

    def get_user_by_email(self, email: str) -> dict:
        """
        Fetches the full user profile by email.
        """
        return self.users_col.find_one({"email": email}, {"_id": 0})
        
    def update_guild_invite_status(self, email: str, status: str) -> bool:
        """
        Updates the user's guild invite status (e.g. 'accepted', 'declined').
        """
        result = self.users_col.update_one(
            {"email": email},
            {"$set": {"guild_invite_status": status, "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    def process_all_unstaged(self):
        """
        Iterates through the raw events in the Landing Zone and formats them for the Graph.
        Uses 'staged' status to track progress across the 13.5k event history.
        """
        # Find raw events not yet formatted
        raw_events = list(self.raw_col.find({"sync_status": "staged"}))
        
        print("--- Processing Raw Events for Formatting ((bulk upsert) ---")
        
        formatted_ops = []
        raw_ops = []
        success_count = 0
        batch_size = 1000  # Adjust based on performance testing
        for raw in raw_events:
            try:
                # The logic for 'HOW' to parse is delegated to calendar_parser.py
                fmt = parse_single_event(raw)
                
                if fmt:
                    formatted_ops.append(
                        UpdateOne(
                            {"gcal_id": fmt.get('gcal_id')}, 
                            {"$set": fmt}, 
                            upsert=True
                        )
                    )

                raw_ops.append(
                    UpdateOne(
                        {"_id": raw["_id"]},
                        {"$set": {"sync_status": "formatted"}}
                    )
                )
                
                success_count += 1
        
                if len(raw_ops) >= batch_size:
                    if formatted_ops:
                        self.formatted_col.bulk_write(formatted_ops, ordered=False)
                    if raw_ops:
                        self.raw_col.bulk_write(raw_ops, ordered=False)
                            
                    # Clear the lists for the next batch
                    formatted_ops = []
                    raw_ops = []
                    print(f"Beautifully processed batch... Total so far: {success_count}")

            except Exception as e:
                print(f"Minor hiccup processing raw event {raw.get('_id')}: {e}")         

        if formatted_ops:
            self.formatted_col.bulk_write(formatted_ops, ordered=False)
        if raw_ops:
            self.raw_col.bulk_write(raw_ops, ordered=False)
                
        print(f"Successfully formatted {success_count} events.")
        return success_count



    def get_formatted_for_neo4j(self):
        """
        A helper to fetch events from Mongo that haven't been 
        successfully processed into the Neo4j graph yet.
        """
        # Look for events where we haven't set a 'neo4j_synced' flag
        return list(self.formatted_col.find({"neo4j_synced": {"$ne": True}}))

    def mark_neo4j_synced(self, gcal_ids):
        """
        Finalizes the pipeline status once data hits the Neo4j Graph.
        """
        self.formatted_col.update_many(
            {"gcal_id": {"$in": gcal_ids}},
            {
                "$set": {
                    "neo4j_synced": True, 
                    "neo4j_last_sync": datetime.now(timezone.utc)
                }
            }
        )

# --- Execution Entry Point ---
if __name__ == "__main__":
        # Ensure environment variables are loaded if running manually
    #os.environ["MONGO_URI"] = 
    
    storage = SovereignMongoStorage()
    
    print(f"Sovereign Storage initiated at {datetime.now(timezone.utc)}")
    processed = storage.process_all_unstaged()
    
    # Final Verification
    if processed > 0:
        print(f"Ready for Graph Ingestion: {len(storage.get_formatted_for_neo4j())} events.")
