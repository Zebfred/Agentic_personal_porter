import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pymongo import MongoClient

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
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client['porter_mach2']
        self.raw_collection = self.db['raw_calendar_events']

    def get_gcal_service(self):
        """Authenticates and returns the GCal service."""
        creds = None
        # Path resolution using .auth strategy
        token_path = '.auth/token.json'
        creds_path = '.auth/credentials.json'

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.scopes)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    raise FileNotFoundError(f"Missing {creds_path}. Please add your GCal credentials.")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, self.scopes)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

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
        
        now = datetime.datetime.utcnow()
        start_time = (now - datetime.timedelta(days=days)).isoformat() + 'Z'
        
        print(f"--- Accessing GCal: Fetching events since {start_time} ---")
        
        try:
            events_result = service.events().list(
                calendarId='primary', 
                timeMin=start_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
        except Exception as e:
            print(f"Error accessing Google Calendar API: {e}")
            return 0
        
        events = events_result.get('items', [])
        
        if not events:
            print("No new events found.")
            return 0

        ops_count = 0
        for event in events:
            event_id = event.get('id')
            # Extract basic fields for the NoSQL Index
            payload = {
                "gcal_id": event_id,
                "summary": event.get('summary', 'No Title'),
                "start": event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
                "end": event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
                "raw_data": event,
                "porter_ingested_at": datetime.datetime.utcnow(),
                "sync_status": "staged", # Staged in Mongo, not yet in Neo4j
                "classification_verified": False
            }

            # Upsert into MongoDB based on GCal Unique ID
            self.raw_collection.update_one(
                {"gcal_id": event_id},
                {"$set": payload},
                upsert=True
            )
            ops_count += 1

        print(f"Successfully synced {ops_count} events to MongoDB Landing Zone.")
        return ops_count

    def verify_landing_zone(self):
        """
        Simple verification of the NoSQL buffer contents.
        """
        total = self.raw_collection.count_documents({})
        staged = self.raw_collection.count_documents({"sync_status": "staged"})
        print(f"\n--- Landing Zone Status ---")
        print(f"Total Events Stored: {total}")
        print(f"Events Pending Neo4j Sync: {staged}")
        
        if total > 0:
            latest = self.raw_collection.find_one(sort=[("start", -1)])
            print(f"Most Recent Event: {latest.get('summary')} ({latest.get('start')})")

if __name__ == "__main__":
    sync = SovereignCalendarSync()
    # Perform a 30-day pull for verification tonight
    sync.pull_large_batch(days=30)
    sync.verify_landing_zone()