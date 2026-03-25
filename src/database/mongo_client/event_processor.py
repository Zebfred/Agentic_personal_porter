import sys
from pathlib import Path
from datetime import datetime, timezone

root = Path(__file__).resolve().parent.parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from src.config import MongoConfig
from src.database.mongo_client.connection import MongoConnectionManager
from src.database.mongo_client.uuid_manager import UUIDGenerator
from src.integrations.calendar_parser import determine_category, event_record_type
from dateutil import parser

class EventProcessorClient:
    """
    Handles routing Google Calendar Events into the specific:
    Intent, Actual, and Unified (Delta) Collections.
    """
    def __init__(self):
        self.db = MongoConnectionManager.get_db()
        self.intent_col = self.db[MongoConfig.INTENT_COLLECTION]
        self.actual_col = self.db[MongoConfig.ACTUAL_COLLECTION]
        self.unified_col = self.db[MongoConfig.UNIFIED_EVENTS_COLLECTION]

    def _calculate_delta(self, intent_duration: int, actual_energy: int) -> dict:
        """
        Placeholder logic for calculating alignment score and unaccounted minutes.
        """
        # This will be expanded as the agent logic gets more sophisticated
        return {
            "alignment_score": 1.0 if actual_energy > 0 else 0.0,
            "unaccounted_minutes": 0 # Default placeholder
        }

    def process_and_route_event(self, raw_gcal_event: dict):
        """
        Takes raw json from the Timeseries collection, parses it, and
        routes it to the correct Intent/Actual/Unified representations.
        """
        gcal_id = raw_gcal_event.get('id')
        if not gcal_id:
            return None
            
        event_uuid = UUIDGenerator.generate_for_event(gcal_id)
        
        # 1. Parse base details
        start_str = raw_gcal_event.get('start', {}).get('dateTime') or raw_gcal_event.get('start', {}).get('date')
        end_str = raw_gcal_event.get('end', {}).get('dateTime') or raw_gcal_event.get('end', {}).get('date')
        
        if not start_str or not end_str:
            return None
            
        start_dt = parser.parse(start_str)
        end_dt = parser.parse(end_str)
        duration_mins = int((end_dt - start_dt).total_seconds() / 60)
        
        title = raw_gcal_event.get('summary', 'Untitled')
        color_id = raw_gcal_event.get('colorId', '1')
        
        # Determine category (Pillar/Subcategory)
        category_data = determine_category(title, color_id)
        record_type = event_record_type(raw_gcal_event)
        
        # Build Standard Payload Block
        base_payload = {
            "title": title,
            "pillar_id": category_data.get("pillar"),
            "subcategory": category_data.get("subcategory"),
            "duration_minutes": duration_mins
        }
        
        # Time slot
        time_slot = {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat()
        }

        # Handle Routing based on Record Type
        # Assuming all events start as Intention unless modified after the start time.
        
        # 1. Update Intention Collection (Only if it's new or originally an intention)
        # We always want a baseline intention if possible.
        self.intent_col.update_one(
            {"_id": event_uuid},
            {"$set": {
                "user_id": "hero_01", # hardcoded for Single Tenant alpha
                "gcal_id": gcal_id,
                "time_slot": time_slot,
                "intent": base_payload,
                "metadata": {
                    "source": "google_calendar",
                    "last_sync": datetime.now(timezone.utc).isoformat()
                }
            }},
            upsert=True
        )
        
        # 2. Update Actual Collection (Only if it has been touched/is an actual log)
        actual_payload = None
        if record_type == "Actual":
            actual_payload = {
                "title": title, # Usually the same, but maybe modified
                "category": category_data.get("pillar"),
                "energy_spent": duration_mins, # placeholder mapped to minutes
                "notes": raw_gcal_event.get("description", ""),
                "status": "Logged"
            }
            self.actual_col.update_one(
                {"_id": event_uuid},
                {"$set": {
                    "user_id": "hero_01",
                    "gcal_id": gcal_id,
                    "time_slot": time_slot,
                    "actual": actual_payload,
                    "metadata": {
                        "source": "google_calendar",
                        "last_sync": datetime.now(timezone.utc).isoformat()
                    }
                }},
                upsert=True
            )
            
        # 3. Update Unified Collection
        # This allows a single query to calculate the Delta natively, exactly as requested.
        # We perform an upsert that specifically sets the fields independently so Actuals don't overwrite Intents.
        
        unified_update = {
            "$set": {
                "user_id": "hero_01",
                "time_slot": time_slot,
                "metadata": {
                    "source": "google_calendar",
                    "last_sync": datetime.now(timezone.utc).isoformat()
                }
            }
        }
        
        # Note: If it's pure intent, we set it. 
        # By separating the payload injections, atomicity is preserved on the actual updates.
        if record_type == "Intention":
            unified_update["$set"]["intent"] = base_payload
        elif record_type == "Actual" and actual_payload:
            unified_update["$set"]["actual"] = actual_payload
            unified_update["$set"]["delta"] = self._calculate_delta(duration_mins, actual_payload["energy_spent"])

        self.unified_col.update_one(
            {"_id": event_uuid},
            unified_update,
            upsert=True
        )
        
        return event_uuid
