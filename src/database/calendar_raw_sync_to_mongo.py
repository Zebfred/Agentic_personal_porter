import logging
from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os
import sys
import json
import logging
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pymongo import MongoClient, UpdateOne
from datetime import datetime, timedelta, timezone, UTC

from src.integrations.google_calendar_authentication_helper import get_calendar_credentials
from src.config import MongoConfig

# Ensure we can import from the src directory
# --- SECURITY WARNING ---
# Ensure .auth/credentials.json and .auth/token.json are in your .gitignore.
# ------------------------

class SovereignCalendarSync:
    """
    Handles the 'Landing Zone' ingestion from GCal to MongoDB.
    This creates a raw audit trail before processing into Neo4j.
    """
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        # Prioritize ENV for security, fallback for local dev
        self.mongo_uri = MongoConfig.MONGO_URI
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[MongoConfig.DB_NAME]
        self.raw_collection = self.db[MongoConfig.RAW_COLLECTION]
        
        # Use the timeseries client for writing to the new architecture
        from src.database.mongo_client.calendar_timeseries import CalendarTimeseriesClient
        self.ts_client = CalendarTimeseriesClient()

    def get_gcal_service(self, refresh_token=None):
        """Authenticates and returns the GCal service."""
        from src.integrations.google_calendar_authentication_helper import get_calendar_credentials_for_user, get_calendar_credentials
        if refresh_token:
            creds = get_calendar_credentials_for_user(refresh_token, scopes=self.scopes)
        else:
            creds = get_calendar_credentials(scopes=self.scopes)
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)

    def pull_sliding_window(self, user_email="Hero", refresh_token=None):
        """
        Standard sync for cron jobs. Fetches a rolling window (now - 7 days to now + 30 days)
        to ensure current events, modifications, and near-future events are constantly updated.
        """
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(days=7)
        end_time = now + timedelta(days=30)
        return self._execute_pull(start_time, end_time, user_email, refresh_token)

    def pull_historical_backlog(self, user_email="Hero", refresh_token=None, oldest_cursor=None):
        """
        Fetches 30 days of history prior to the oldest_cursor.
        Returns the number of operations and the new cursor date.
        """
        if not oldest_cursor:
            oldest_cursor = datetime.now(timezone.utc)
            
        start_time = oldest_cursor - timedelta(days=30)
        end_time = oldest_cursor
        
        logger.info(f"!!! Initiating Historical Pull from {start_time} to {end_time} for {user_email} !!!")
        ops_count = self._execute_pull(start_time, end_time, user_email, refresh_token)
        return ops_count, start_time

    def _execute_pull(self, start_time, end_time, user_email, refresh_token):
        """
        Internal execution logic for GCal -> MongoDB.
        """
        service = self.get_gcal_service(refresh_token)
        
        # Ensure RFC3339 compliance for GCal API
        start_rfc3339 = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_rfc3339 = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        logger.info(f"--- Accessing GCal: Fetching events from {start_rfc3339} to {end_rfc3339} ---")

        ops_count = 0
        api_calls = 0
        page_token = None

        while True:
            try:
                api_calls += 1
                events_result = service.events().list(
                    calendarId='primary', 
                    timeMin=start_rfc3339,
                    timeMax=end_rfc3339,
                    singleEvents=True,
                    orderBy='startTime',
                    pageToken=page_token
                ).execute()
            except Exception as e:
                logger.info(f"Error accessing Google Calendar API: {e}")
                break
            
            events = events_result.get('items', [])
            
            if not events:
                logger.info("No new events found.")
                break

            bulk_ops = []
            for event in events:
                event_id = event.get('id')
                
                # 1. Standard Landing Zone (For Downstream CrewAI sync pipeline)
                payload = {
                    "gcal_id": event_id,
                    "user_email": user_email,
                    "summary": event.get('summary', 'No Title'),
                    "start": event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
                    "end": event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
                    "raw_data": event,
                    "porter_ingested_at": datetime.now(timezone.utc),
                    "sync_status": "staged", # Staged in Mongo, not yet in Neo4j
                    "classification_verified": False
                }

                # Add to bulk operations based on GCal Unique ID
                bulk_ops.append(UpdateOne(
                    {"gcal_id": event_id},
                    {"$set": payload},
                    upsert=True
                ))
                
                # 2. Native Time-Series Dual-Write
                success = self.ts_client.stage_raw_event(event, user_email=user_email)
                
                # Increment operation count
                ops_count += 1

            if bulk_ops:
                self.raw_collection.bulk_write(bulk_ops, ordered=False)

            page_token = events_result.get('nextPageToken')
            if not page_token:
                break

        logger.info(f"API Rate Info: Made {api_calls} request(s) to Google Calendar API.")
        logger.info(f"Successfully synced {ops_count} events to MongoDB Landing Zone.")
        return ops_count

    def verify_landing_zone(self):
        """
        Simple verification of the NoSQL buffer contents.
        """
        total = self.raw_collection.count_documents({})
        staged = self.raw_collection.count_documents({"sync_status": "staged"})
        
        ts_total = self.ts_client.timeseries_col.count_documents({})
        
        logger.info("\n--- Dual-Track Landing Zone Status ---")
        logger.info(f"Total Standard Events Stored: {total}")
        logger.info(f"Events Pending Neo4j Sync: {staged}")
        logger.info(f"Total Native TS Events Stored: {ts_total}")
        
        if total > 0:
            latest = self.raw_collection.find_one(sort=[("start", -1)])
            logger.info(f"Most Recent Event: {latest.get('summary')} ({latest.get('start')})")

if __name__ == "__main__":
    sync = SovereignCalendarSync()
    # Perform a 90-day pull for verification tonight
    sync.pull_large_batch(days=90)
    sync.verify_landing_zone()