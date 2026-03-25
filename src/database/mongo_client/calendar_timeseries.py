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
        self.timeseries_col = self.db[MongoConfig.RAW_TIMESERIES_COLLECTION]
        self.processor = EventProcessorClient()

    def stage_raw_event(self, gcal_event: dict) -> bool:
        """
        Upserts the completely raw JSON from google calendar into the timeseries collection.
        Automatically triggers the downstream processor to route to intent/actual schemas.
        """
        gcal_id = gcal_event.get('id')
        if not gcal_id:
            return False
            
        payload = {
            "gcal_id": gcal_id,
            "raw_data": gcal_event,
            "porter_ingested_at": datetime.now(timezone.utc).isoformat(),
            "sync_status": "staged"
        }
        
        # Save as a timeseries event
        self.timeseries_col.update_one(
            {"gcal_id": gcal_id},
            {"$set": payload},
            upsert=True
        )
        
        # Trigger downstream processor to split into schemas
        try:
           self.processor.process_and_route_event(gcal_event)
           # Mark as completely mapped
           self.timeseries_col.update_one(
               {"gcal_id": gcal_id},
               {"$set": {"sync_status": "formatted_and_routed"}}
           )
           return True
        except Exception as e:
           print(f"Error processing event {gcal_id}: {e}")
           return False
