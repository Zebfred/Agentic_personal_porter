import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Neo4j Connection Details ---
# Make sure to add these to your .env file
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))

def get_driver():
    """Establishes connection with the Neo4j database."""
    return GraphDatabase.driver(URI, auth=AUTH)

def close_driver(driver):
    """Closes the database connection."""
    if driver:
        driver.close()

def log_to_neo4j(log_data):
    """
    Takes a dictionary of log data and creates corresponding nodes and
    relationships in the Neo4j database.
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.write_transaction(_create_log_entry, log_data)
    close_driver(driver)
    return result

def _create_log_entry(tx, log_data):
    """
    A private function that executes the Cypher query to create the graph structure.
    This represents a single, atomic transaction.
    """
    # For this MVP, we'll use a hardcoded user ID.
    # In a real app, this would come from a user session.
    user_id = "hero_user"

    # The Cypher query to build our graph structure
    # MERGE is like "find or create", preventing duplicate nodes.
    query = """
    // 1. Find or create the User and the Day nodes
    MERGE (u:User {id: $user_id})
    MERGE (d:Day {date: $log_data.day})
    MERGE (u)-[:HAS_LOG_FOR]->(d)

    // 2. Create the TimeChunk and connect it to the Day
    CREATE (tc:TimeChunk {name: $log_data.timeChunk})
    MERGE (d)-[:HAS_CHUNK]->(tc)

    // 3. Create the Intention and connect it to the TimeChunk
    CREATE (i:Intention {title: $log_data.intention})
    MERGE (tc)-[:HAD_INTENTION]->(i)

    // 4. Create the Actual activity and connect it
    CREATE (a:Actual {
        title: $log_data.actual,
        feeling: $log_data.feeling,
        brainFog: $log_data.brainFog
    })
    MERGE (tc)-[:LOGGED_ACTUAL]->(a)

    // 5. Create the Reflection and connect it to the Actual
    CREATE (r:Reflection {text: $log_data.reflection})
    MERGE (a)-[:GENERATED_REFLECTION]->(r)

    // 6. If it's a Valuable Detour, add that label and relationship
    WITH a
    WHERE $log_data.isValuableDetour = true
    SET a:ValuableDetour
    CREATE (vd:DetourNote {text: $log_data.inventoryNote})
    MERGE (a)-[:HAS_NOTE]->(vd)

    RETURN 'Log successfully created in Neo4j'
    """
    result = tx.run(query, user_id=user_id, log_data=log_data)
    return result.single()[0]
