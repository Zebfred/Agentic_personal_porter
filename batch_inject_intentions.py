import json
import os
import glob
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load credentials
load_dotenv()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD"))

def get_latest_formatted_file():
    """Finds the most recent formatted month file in the data directory."""
    list_of_files = glob.glob('data/google_calendar/month_formatted_*.json')
    #list_of_files = glob.glob('data/google_calendar/month_sample.json')
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)

def inject_intentions(file_path):
    with open(file_path, 'r') as f:
        intentions = json.load(f)

    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    # The "Magic" Cypher Query
    # 1. Unwinds the list into individual 'row' objects
    # 2. Merges the Intention node by source_id to prevent duplicates
    # 3. Connects it to the User (Jimmy)
    cypher_query = """
    UNWIND $batch AS row
    MERGE (i:Intention {source_id: row.source_id})
    SET i.title = row.title,
    i.description = row.context_notes,
    i.start_time = datetime(row.timing.start_iso),
    i.duration_minutes = row.timing.duration_minutes,
    i.category = row.meta.category_hint
    i.google_color_id = row.meta.google_color_id,
    i.initial_hint = row.meta.category_hint, // Use the parser's hint as a starting point
    i.status = 'unprocessed' // This tells the Agent: "Categorize Me"
    
    WITH i
    MATCH (u:User {name: 'Jimmy'}) // Assumes your user node exists
    MERGE (u)-[:INTENDED]->(i)
    RETURN count(i) as total
    """

    with driver.session() as session:
        result = session.run(cypher_query, batch=intentions)
        summary = result.single()
        print(f"✅ Successfully injected {summary['total']} intentions into the graph.")

    driver.close()

if __name__ == "__main__":
    latest_file = get_latest_formatted_file()
    if latest_file:
        print(f"📂 Processing: {latest_file}")
        inject_intentions(latest_file)
    else:
        print("❌ No formatted data files found. Run your month fetch script first!")