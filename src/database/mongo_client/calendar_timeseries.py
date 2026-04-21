import sys
from pathlib import Path
from datetime import datetime, timezone

root = Path(__file__).resolve().parent.parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from src.config import MongoConfig
from src.database.mongo_client.connection import MongoConnectionManager
from src.database.mongo_client.event_processor import EventProcessorClient

class CalendarTimeseriesClient:
    """
    Handles the raw ingestion (Timeseries collection) of Google Calendar events,
    acting as the unchanged audit trail buffer before agent parsing.
    """
    def __init__(self):
        self.db = MongoConnectionManager.get_db()
        collection_name = MongoConfig.RAW_TIMESERIES_COLLECTION
        
        # Initialize native MongoDB Time-Series collection if missing
        if collection_name not in self.db.list_collection_names():
            try:
                self.db.create_collection(
                    collection_name,
                    timeseries={
                        'timeField': 'start_time',
                        'metaField': 'metadata',
                        'granularity': 'minutes'
                    }
                )
                print(f"Created native Time-Series collection: {collection_name}")
            except Exception as e:
                print(f"Ensuring Time-Series collection exist failed/skipped: {e}")
                
        self.timeseries_col = self.db[collection_name]
        self.processor = EventProcessorClient()

    def stage_raw_event(self, gcal_event: dict) -> bool:
        """
        Upserts the completely raw JSON from google calendar into the timeseries collection.
        Automatically triggers the downstream processor to route to intent/actual schemas.
        """
        gcal_id = gcal_event.get('id')
        if not gcal_id:
            return False
            
        # Parse Google Calendar start time to python datetime for timeField
        start_raw = gcal_event.get('start', {}).get('dateTime') or gcal_event.get('start', {}).get('date')
        if not start_raw:
            return False
            
        try:
            if start_raw.endswith('Z'):
                start_raw = start_raw.replace('Z', '+00:00')
            start_dt = datetime.fromisoformat(start_raw)
        except Exception:
            start_dt = datetime.now(timezone.utc)
            
        payload = {
            "start_time": start_dt,
            "metadata": {
                "gcal_id": str(gcal_id),
                "sync_status": "staged",
                "event_type": str(gcal_event.get("eventType", "default"))
            },
            "raw_data": gcal_event,
            "porter_ingested_at": datetime.now(timezone.utc)
        }
        
        # Insert as a true timeseries historical event audit log
        try:
            self.timeseries_col.insert_one(payload)
        except Exception as e:
            print(f"Failed to insert timeseries event for gcal_id {gcal_id}: {e}")
            return False
        
        # Trigger downstream processor to split into schemas
        try:
           self.processor.process_and_route_event(gcal_event)
           return True
        except Exception as e:
           print(f"Error processing event {gcal_id}: {e}")
           return False
