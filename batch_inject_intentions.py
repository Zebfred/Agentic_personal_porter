import json
import os
import glob
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load credentials
load_dotenv()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD"))
USER_NAME = "Jimmy" # The "Hero" of this journey

def get_latest_formatted_file():
    """Finds the most recent formatted calendar file."""
    list_of_files = glob.glob('data/google_calendar/month_formatted_*.json')
    if not list_of_files:
        # Check for the sample file if no fresh ones exist
        if os.path.exists('data/google_calendar/month_sample.json'):
            return 'data/google_calendar/month_sample.json'
        return None
    return max(list_of_files, key=os.path.getctime)

def inject_intentions(file_path):
    print(f"📖 Reading data from: {file_path}")
    with open(file_path, 'r') as f:
        intentions = json.load(f)

    driver = GraphDatabase.driver(URI, auth=AUTH)

    # The "Personal Porter" Injection Logic:
    # 1. MERGE Intention by source_id (Idempotent - won't duplicate)
    # 2. SET properties including our new 'label' and 'is_processed'
    # 3. CONNECT to the User (Jimmy)
    # 4. CONNECT to a Day node (Timeline anchor)
    cypher_query = """
    UNWIND $batch AS row
    MERGE (i:Intention {source_id: row.source_id})
    SET i.title = row.title,
        i.description = row.context_notes,
        i.start_time = datetime(row.timing.start_iso),
        i.end_time = datetime(row.timing.end_iso),
        i.duration_minutes = row.timing.duration_minutes,
        i.time_chunk = row.timing.time_chunk,
        i.google_color_id = row.meta.google_color_id,
        i.label = row.meta.label,
        i.is_processed = row.meta.is_processed,
        i.updated_at = datetime()
    
    WITH i, row
    MATCH (u:User {name: $user_name})
    MERGE (u)-[:INTENDED]->(i)
    
    WITH i, row
    MERGE (d:Day {date: substring(row.timing.start_iso, 0, 10)})
    MERGE (i)-[:ON_DAY]->(d)
    
    RETURN count(i) as total
    """
    
    try:
        with driver.session() as session:
            result = session.run(cypher_query, batch=intentions, user_name=USER_NAME)
            summary = result.single()
            print(f"✅ SUCCESSFULLY INJECTED {summary['total']} INTENTIONS.")
            print(f"🔗 Linked to User: '{USER_NAME}' and their respective 'Day' nodes.")
    except Exception as e:
        print(f"❌ Error during injection: {e}")
    finally:
        driver.close()


if __name__ == "__main__":
    latest_file = get_latest_formatted_file()
    if latest_file:
        print(f"📂 Processing: {latest_file}")
        inject_intentions(latest_file)
    else:
        print("❌ No formatted data files found. Run your month fetch script first!")