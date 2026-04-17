import os
import sys
from pathlib import Path
from typing import List, Dict

from src.database.mongo_client.connection import MongoConnectionManager
from src.config import MongoConfig

class TimeKeeperAgent:
    """
    The Temporal Specialist Agent.
    Queries native MongoDB time-series arrays to answer time-based constraints,
    historical rolling facts, and calendar boundaries.
    """
    def __init__(self):
        self.db = MongoConnectionManager.get_db()
        self.ts_col = self.db[MongoConfig.RAW_TIMESERIES_COLLECTION]
        
    def get_events_in_range(self, start_date_iso: str, end_date_iso: str) -> List[Dict]:
        """
        Query the rolling historical timeseries block within a specific window.
        """
        from dateutil import parser
        try:
            start_dt = parser.parse(start_date_iso)
            end_dt = parser.parse(end_date_iso)
        except Exception as e:
            print(f"TimeKeeper Date Parsing Error: {e}")
            return []
            
        pipeline = [
            {"$match": {
                "start_time": {"$gte": start_dt, "$lte": end_dt}
            }},
            {"$sort": {"start_time": 1}},
            {"$limit": 50}
        ]
        
        records = list(self.ts_col.aggregate(pipeline))
        
        for r in records:
             if "_id" in r:
                 r["_id"] = str(r["_id"])
        return records

    def summarize_day(self, date_iso: str) -> str:
        """
        Retrieves a high-level summary of a specific day to feed the Porter.
        """
        from datetime import timedelta
        from dateutil import parser
        try:
            start_dt = parser.parse(date_iso).replace(hour=0, minute=0, second=0)
            end_dt = start_dt + timedelta(days=1)
            
            events = self.get_events_in_range(start_dt.isoformat(), end_dt.isoformat())
            if not events:
                return f"No temporal events resolved for {date_iso}."
                
            summaries = [f"- {e.get('raw_data', {}).get('summary', 'Unknown Event')} at {e.get('start_time')}" for e in events]
            return f"TimeKeeper Summary for {date_iso}:\n" + "\n".join(summaries)
        except Exception as e:
            return f"TimeKeeper Error: {e}"
