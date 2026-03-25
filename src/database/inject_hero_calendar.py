from neo4j import GraphDatabase
import sys
import os
from pathlib import Path
    
# Ensure we can import from the src directory when running from helper_scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.config import NeoConfig
from src.constants import ACTUAL_CATEGORY_MAPPING

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
        self.driver = GraphDatabase.driver(
            NeoConfig.NEO4J_URI, 
            auth=(NeoConfig.NEO4J_USER, NeoConfig.NEO4J_PASS)
        )

    def close(self):
        self.driver.close()

    def inject_calendar_to_graph(self, formatted_events, hero_name=None):
        import os
        if hero_name is None:
            hero_name = os.environ.get("HERO_NAME", "Hero")
        """
        Takes the 'Golden Objects' into wires them into the existing Hero/Intent graph.
        """
        # Pre-process the events in Python to attach the precise Graph Intent Target
        for event in formatted_events:
            pillar = event.get("pillar", "Uncategorized")
            # Translate "Career related" to "Career Goal" using your dynamic map
            event["graph_intent_target"] = self.REVERSE_INTENT_MAP.get(pillar, pillar)
            
            # Neo4j cannot serialize Mongo ObjectIds, so we remove it
            if '_id' in event:
                del event['_id']
            
            # Neo4j python driver prefers string ISOs rather than datetime objects for dict params
            if 'processed_at' in event and not isinstance(event['processed_at'], str):
                event['processed_at'] = str(event['processed_at'])

        # This query creates the Event and links it to the Intent from hero_ambition.json
        # using the 'pillar' (e.g., 'Career related') as the bridge.
        query = """
        MATCH (h:Hero {name: $hero_name})
        
        // 1. Ensure a Calendar node exists for the Hero
        MERGE (h)-[:HAS_CALENDAR]->(c:Calendar {name: "Primary"})
        
        WITH h, c
        UNWIND $events AS event_data
        
        // 2. Create the Event Node using GCal ID for Idempotency
        MERGE (e:Event {gcal_id: event_data.gcal_id})
        SET e.title = event_data.title,
            e.start_iso = event_data.start,
            e.duration_min = event_data.duration_minutes,
            e.record_type = event_data.record_type,
            e.pillar = event_data.pillar,
            e.subcategory = event_data.subcategory,
            e.processed_at = datetime()
            
        MERGE (c)-[:HAS_EVENT]->(e)
        
        // 3. Bridge to Intent nodes based on Pillar/Category
        // We match the 'pillar' from the parser to the 'category' in the Intent nodes
        WITH e, event_data
        MATCH (i:Intent)
        WHERE i.category = event_data.graph_intent_target 
           OR i.category = event_data.subcategory
        MERGE (e)-[:FULFILLS]->(i)
        
        RETURN count(e) as injected_count
        """

        try:
            with self.driver.session() as session:
                result = session.run(query, hero_name=hero_name, events=formatted_events)
                summary = result.single()
                return summary["injected_count"] if summary else 0
        except Exception as e:
            print(f"![GRAPH ERROR]: Failed to inject events: {e}")
            return 0

if __name__ == "__main__":
    # Test block for manual verification
    injector = SovereignGraphInjector()
    try:
        sample_mongo_payload = [{
            "gcal_id": "63ervd579l8n4aoqh4dj0mp0io",
            "duration_minutes": 75,
            "pillar": "Career related",
            "processed_at": "2026-03-16T10:42:38.515566",
            "record_type": "Actual",
            "start": "2026-03-03T09:00:00-06:00",
            "subcategory": "Hero's Work",
            "title": "Replan of implimentation for Porter Project"
        }]
        count = injector.inject_calendar_to_graph(sample_mongo_payload)
        print(f"Injected {count} test events into Neo4j.")
    finally:
        injector.close()