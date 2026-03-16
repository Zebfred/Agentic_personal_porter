import json
from neo4j import GraphDatabase
from src.config import NeoConfig

# Secure Driver Initialization
driver = GraphDatabase.driver(NeoConfig.NEO4J_URI, auth=(NeoConfig.NEO4J_USER, NeoConfig.NEO4J_PASS))

def inject_calendar_to_graph(formatted_events, hero_name="Zeb"):
    """
    Takes the 'Golden Objects' from your calendar_parser.py and 
    wires them into the existing Hero/Intent graph.
    """
    
    # This query creates the Event and links it to the Intent from hero_ambition.json
    # using the 'pillar' (e.g., 'Career related') as the bridge.
    query = """
    MATCH (h:Hero {name: $hero_name})
    
    // 1. Ensure a Calendar node exists for the Hero
    MERGE (h)-[:HAS_CALENDAR]->(c:Calendar {name: "Primary"})
    
    WITH h, c
    UNWIND $events AS event_data
    
    // 2. Create the Event Node
    MERGE (e:Event {source_id: event_data.source_id})
    SET e.title = event_data.title,
        e.start_iso = event_data.timing.start_iso,
        e.duration_min = event_data.timing.duration_minutes,
        e.record_type = event_data.meta.record_type,
        e.processed = event_data.meta.is_processed
        
    MERGE (c)-[:HAS_EVENT]->(e)
    
    // 3. Link the Event to the corresponding Intent
    // We match the 'pillar' from the parser to the 'category' in the Intent nodes
    WITH e, event_data
    MATCH (i:Intent)
    WHERE i.category = event_data.meta.pillar 
       OR i.category = event_data.meta.subcategory
    MERGE (e)-[:FULFILLS]->(i)
    """

    with driver.session() as session:
        session.run(query, hero_name=hero_name, events=formatted_events)
        print(f"✅ Successfully mapped {len(formatted_events)} events to your Hero's Intents!")

# --- Local Test Logic ---
if __name__ == "__main__":
    # In a real run, this would pull from your NoSQL 'Staging' data
    # For now, we use a sample formatted from your calendar_parser.py
    sample_formatted = [
        {
            "source_id": "test_123",
            "title": "Deep Dive on LaUIrl",
            "timing": {"start_iso": "2026-03-11T09:00:00", "duration_minutes": 120},
            "meta": {
                "pillar": "Career related", 
                "subcategory": "Professional-core",
                "record_type": "Actual"
            }
        }
    ]
    
    try:
        inject_calendar_to_graph(sample_formatted)
    finally:
        driver.close()