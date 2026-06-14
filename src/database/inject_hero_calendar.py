from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os
from datetime import datetime
    
# Ensure we can import from the src directory when running from helper_scripts

from src.constants import ACTUAL_CATEGORY_MAPPING
from src.database.neo4j_client.connection import get_driver
from src.database.inject_hero_foundation import get_or_create_time_chunk

class SovereignGraphInjector:
    """
    Handles the high-stakes MERGE logic into the Neo4j Identity Graph.
    Uses the 'Twin-Track' ingestion logic to separate Intent from Actual.
    """
    # Programmatically reverse your dictionary so we map Mongo Pillar -> Neo4j Intent
    REVERSE_INTENT_MAP = {
        v: k for k, v in ACTUAL_CATEGORY_MAPPING["intent_to_actual_mapping"].items()
    }

    def __init__(self):
        self.driver = get_driver()

    def close(self):
        if hasattr(self, 'driver') and self.driver:
            self.driver.close()

    def inject_calendar_to_graph(self, formatted_events, user_email=None, username="system"):
        if user_email is None:
            user_email = os.environ.get("NEXUS_ADMIN_EMAIL", "")
        if not user_email:
            raise ValueError("user_email is required: pass it explicitly or set NEXUS_ADMIN_EMAIL env var.")
        
        intent_events = []
        actual_events = []
        
        # Pre-process the events in Python to attach the TimeChunk and route them
        for event in formatted_events:
            pillar = event.get("pillar", "Uncategorized")
            # Translate "Career related" to "Career Goal" using your dynamic map
            event["graph_intent_target"] = self.REVERSE_INTENT_MAP.get(pillar, pillar)
            
            # Neo4j cannot serialize Mongo ObjectIds, so we remove it
            if '_id' in event:
                del event['_id']
            
            # Convert start time to Python datetime object for the time chunk generator
            start_iso = event.get("start")
            if start_iso:
                try:
                    dt = datetime.fromisoformat(start_iso)
                    time_chunk_id = get_or_create_time_chunk(self.driver, dt, username)
                    event["time_chunk_id"] = time_chunk_id
                except ValueError:
                    logger.info(f"Warning: Invalid start ISO format {start_iso}")
                    event["time_chunk_id"] = None
            else:
                event["time_chunk_id"] = None

            # Neo4j python driver prefers string ISOs rather than datetime objects for dict params
            if 'processed_at' in event and not isinstance(event['processed_at'], str):
                event['processed_at'] = str(event['processed_at'])
                
            # Route to correct track
            if event.get("record_type") == "Actual":
                # Ensure defaults for match logic exist
                event["matches_intent"] = event.get("matches_intent", False)
                event["is_valuable_detour"] = event.get("is_valuable_detour", False)
                actual_events.append(event)
            else:
                intent_events.append(event)

        injected_count = 0

        # --- QUERY 1: INTENT INJECTION ---
        intent_query = """
        UNWIND $events AS event_data
        
        // 1. Locate the correct TimeChunk
        MATCH (tc:TimeChunk {id: event_data.time_chunk_id})
        
        // 2. Create the Intent node for the calendar event
        MERGE (i:Intent {gcal_id: event_data.gcal_id, user_email: $user_email})
        SET i.title = event_data.title,
            i.start_iso = event_data.start,
            i.duration_min = event_data.duration_minutes,
            i.type = "Calendar Event",
            i.subcategory = event_data.subcategory,
            i.processed_at = datetime()
            
        // 3. Link TimeChunk -> Intent (The One-Way Valve)
        MERGE (tc)-[:PLANNED_AS]->(i)
        
        // 4. Bridge to the classified Pillar
        WITH i, event_data
        MATCH (p:Pillar {name: event_data.pillar})
        MERGE (i)-[:CLASSIFIED_AS]->(p)
        
        RETURN count(i) as count
        """

        # --- QUERY 2: ACTUAL INJECTION ---
        actual_query = """
        UNWIND $events AS entry
        
        // 1. Locate the correct TimeChunk
        MATCH (tc:TimeChunk {id: entry.time_chunk_id})
        
        // 2. Create the Actual node
        MERGE (a:Actual {id: entry.gcal_id, user_email: $user_email}) // Using gcal_id as ID for idempotency if applicable
        SET a.description = entry.title,
            a.start_iso = entry.start,
            a.duration_min = entry.duration_minutes,
            a.human_confirmed = entry.human_confirmed,
            a.processed_at = datetime()
            
        // 3. Link TimeChunk -> Actual (The One-Way Valve)
        MERGE (tc)-[:RECORDED_AS]->(a)
        
        // 4. Bridge to the classified Pillar
        WITH a, tc, entry
        MATCH (p:Pillar {name: entry.pillar})
        MERGE (a)-[:CLASSIFIED_AS]->(p)
        
        // 5. Execution Evaluation (Match vs Not Match)
        // We look up the Intent that was planned for this same TimeChunk
        WITH a, tc, entry
        OPTIONAL MATCH (tc)-[:PLANNED_AS]->(i:Intent)
        
        // If an Intent exists and it's a match:
        FOREACH (_ IN CASE WHEN i IS NOT NULL AND entry.matches_intent THEN [1] ELSE [] END |
            MERGE (i)-[:MATCH]->(a)
        )
        
        // If an Intent exists and it's a detour:
        FOREACH (_ IN CASE WHEN i IS NOT NULL AND NOT entry.matches_intent THEN [1] ELSE [] END |
            MERGE (i)-[:NOT_MATCH]->(d:Detour {type: CASE WHEN entry.is_valuable_detour THEN "Valuable" ELSE "Detrimental" END})
            MERGE (d)-[:RECORDED_AS]->(a)
        )
        
        RETURN count(a) as count
        """

        try:
            with self.driver.session() as session:
                if intent_events:
                    result_i = session.run(intent_query, user_email=user_email, events=intent_events)
                    summary_i = result_i.single()
                    injected_count += (summary_i["count"] if summary_i else 0)
                
                if actual_events:
                    result_a = session.run(actual_query, user_email=user_email, events=actual_events)
                    summary_a = result_a.single()
                    injected_count += (summary_a["count"] if summary_a else 0)
                    
            return injected_count
        except Exception as e:
            logger.info(f"![GRAPH ERROR]: Failed to inject events: {e}")
            return 0

if __name__ == "__main__":
    # Test block for manual verification
    injector = SovereignGraphInjector()
    try:
        sample_mongo_payload = [
            {
                "gcal_id": "intent_test_123",
                "duration_minutes": 60,
                "pillar": "Career Goal",
                "processed_at": "2026-03-16T10:42:38.515566",
                "record_type": "Intent",
                "start": "2026-03-03T09:00:00-06:00",
                "subcategory": "Deep Work",
                "title": "Planned Work Session"
            },
            {
                "gcal_id": "actual_test_456",
                "duration_minutes": 75,
                "pillar": "Career Goal",
                "processed_at": "2026-03-16T11:42:38.515566",
                "record_type": "Actual",
                "start": "2026-03-03T09:00:00-06:00",
                "subcategory": "Deep Work",
                "title": "Replan of implimentation for Porter Project",
                "human_confirmed": True,
                "matches_intent": True,
                "is_valuable_detour": False
            }
        ]
        count = injector.inject_calendar_to_graph(sample_mongo_payload)
        logger.info(f"Injected {count} test events into Neo4j.")
    finally:
        injector.close()