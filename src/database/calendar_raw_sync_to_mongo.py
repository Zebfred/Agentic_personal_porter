import os
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone, UTC

root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.integrations.google_calendar_authentication_helper import get_calendar_credentials
from src.config import MongoConfig

# Ensure we can import from the src directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# --- SECURITY WARNING ---
# Ensure .auth/credentials.json and .auth/token.json are in your .gitignore.
# ------------------------

class SovereignCalendarSync:
    """
    Handles the 'Landing Zone' ingestion from GCal to MongoDB.
    This creates a raw audit trail before processing into Neo4j.
    """
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        # Prioritize ENV for security, fallback for local dev
        self.mongo_uri = MongoConfig.MONGO_URI
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[MongoConfig.DB_NAME]
        self.raw_collection = self.db[MongoConfig.RAW_COLLECTION]
        
        # Use the timeseries client for writing to the new architecture
        from src.database.mongo_client.calendar_timeseries import CalendarTimeseriesClient
        self.ts_client = CalendarTimeseriesClient()

    def get_gcal_service(self):
        """Authenticates and returns the GCal service."""
        # Use the centralized helper for consistency across the project
        creds = get_calendar_credentials(scopes=self.scopes)
        return build('calendar', 'v3', credentials=creds)

    def pull_recent_events(self, days=7):
        """
        Standard sync for cron jobs. Defaults to 7 days of data.
        """
        return self._execute_pull(days)

    def pull_large_batch(self, days=90):
        """
        Perform a one-time historical pull to populate the Landing Zone.
        """
        print(f"!!! Initiating Large Batch Pull: {days} days of history !!!")
        return self._execute_pull(days)

    def _execute_pull(self, days):
        """
        Internal execution logic for GCal -> MongoDB.
        """
        service = self.get_gcal_service()
        
        now = datetime.now(timezone.utc)
        delta = timedelta(days=days)
        # Ensure RFC3339 compliance for GCal API
        start_time = (now - delta).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        print(f"--- Accessing GCal: Fetching events since {start_time} ---")

        ops_count = 0
        page_token = None

        while True:
            try:
                events_result = service.events().list(
                    calendarId='primary', 
                    timeMin=start_time,
                    singleEvents=True,
                    orderBy='startTime',
                    pageToken=page_token
                ).execute()
            except Exception as e:
                print(f"Error accessing Google Calendar API: {e}")
                break
            
            events = events_result.get('items', [])
            
            if not events:
                print("No new events found.")
                break

            for event in events:
                event_id = event.get('id')
                
                # 1. Standard Landing Zone (For Downstream CrewAI sync pipeline)
                payload = {
                    "gcal_id": event_id,
                    "summary": event.get('summary', 'No Title'),
                    "start": event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
                    "end": event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
                    "raw_data": event,
                    "porter_ingested_at": datetime.now(timezone.utc),
                    "sync_status": "staged", # Staged in Mongo, not yet in Neo4j
                    "classification_verified": False
                }

                # Upsert into MongoDB based on GCal Unique ID
                self.raw_collection.update_one(
                    {"gcal_id": event_id},
                    {"$set": payload},
                    upsert=True
                )
                
                # 2. Native Time-Series Dual-Write
                success = self.ts_client.stage_raw_event(event)
                
                # Increment operation count
                ops_count += 1

            page_token = events_result.get('nextPageToken')
            if not page_token:
                break

        print(f"Successfully synced {ops_count} events to MongoDB Landing Zone.")
        return ops_count

    def verify_landing_zone(self):
        """
        Simple verification of the NoSQL buffer contents.
        """
        total = self.raw_collection.count_documents({})
        staged = self.raw_collection.count_documents({"sync_status": "staged"})
        
        ts_total = self.ts_client.timeseries_col.count_documents({})
        
        print("\n--- Dual-Track Landing Zone Status ---")
        print(f"Total Standard Events Stored: {total}")
        print(f"Events Pending Neo4j Sync: {staged}")
        print(f"Total Native TS Events Stored: {ts_total}")
        
        if total > 0:
            latest = self.raw_collection.find_one(sort=[("start", -1)])
            print(f"Most Recent Event: {latest.get('summary')} ({latest.get('start')})")

if __name__ == "__main__":
    sync = SovereignCalendarSync()
    # Perform a 90-day pull for verification tonight
    sync.pull_large_batch(days=90)
    sync.verify_landing_zone()