import os
import sys
from datetime import datetime, timedelta, time
import logging

# Path setup to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.google_calendar import get_calendar_service
from src.database.mongo_storage import SovereignMongoStorage
from src.database.inject_hero_calendar import SovereignGraphInjector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SeedCalendar")

def seed_past_month():
    """
    Pulls raw calendar data spanning exactly 30 days back from today.
    Saves it to the Mongo landing zone, formats it, and injects to Neo4j.
    """
    logger.info("Initiating 30-Day Historical Calendar Pull.")
    
    # Define Time Bounds
    today = datetime.now()
    start_date = (today - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today.replace(hour=23, minute=59, second=59)
    
    time_min = start_date.isoformat() + 'Z'
    time_max = end_date.isoformat() + 'Z'
    
    logger.info(f"Targeting: {time_min} through {time_max}")
    
    # 1. Fetch from Google
    try:
        service = get_calendar_service()
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=2500
        ).execute()
        
        events = events_result.get('items', [])
        logger.info(f"Retrieved {len(events)} raw events from Google Calendar.")
        
    except Exception as e:
        logger.error(f"Failed to fetch from Google Calendar: {e}")
        return

    # 2. Store loosely in Mongo (The Raw Staging Zone)
    mongo = SovereignMongoStorage()
    
    # Bulk inserting raw events with the "staged" flag for processor
    raw_payloads = []
    for event in events:
        # Avoid duplicate insertions in raw using gcal id as key
        # For simplicity in seeding, we will just upsert
        event["sync_status"] = "staged"
        event["ingested_at"] = today.isoformat()
        
        # Insert them into the raw collection
        mongo.raw_col.update_one(
            {"id": event.get("id")},
            {"$set": event},
            upsert=True
        )
        
    logger.info("Successfully dropped all events into MongoDB raw_calendar_events.")
    
    # 3. Process into Formatted Time-Series Collection
    logger.info("Triggering Time-Series Formatter...")
    formatted_count = mongo.process_all_unstaged()
    logger.info(f"Formatted and refined {formatted_count} events.")
    
    # 4. Inject formatted payload directly into the Central Hero Graph
    logger.info("Beginning Hero Graph Injection...")
    ready_events = mongo.get_formatted_for_neo4j()
    
    if len(ready_events) > 0:
        injector = SovereignGraphInjector()
        neo4j_count = injector.inject_calendar_to_graph(ready_events)
        
        # Mark as strictly synced so they don't resend
        if neo4j_count > 0:
            synced_ids = [e.get('gcal_id') for e in ready_events]
            mongo.mark_neo4j_synced(synced_ids)
            logger.info(f"Successfully bridged {neo4j_count} Events into Neo4j Identity Graph!")
        else:
            logger.warning("No events successfully mapped to Neo4j schema.")
            
        injector.close()
    else:
        logger.info("No formatted events were ready or valid for Neo4j injection.")

if __name__ == "__main__":
    seed_past_month()
