import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# --- Database Connection ---
URI = os.getenv("NEO4J_URI")
AUTH_USER = os.getenv("NEO4J_USERNAME")
AUTH_PASS = os.getenv("NEO4J_PASSWORD")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))


def get_driver():
    """Establishes a connection to the Neo4j database."""
    return GraphDatabase.driver(URI, auth=(AUTH_USER, AUTH_PASS))

# --- Logging Function ---
def log_to_neo4j(log_data: dict) -> str:
    """
    Logs a complete journal entry to the Neo4j database.
    Returns a confirmation message.
    """
    driver = get_driver()
    with driver.session() as session:
        result_node = session.write_transaction(_create_log_entry, log_data)
        
        # another potential fix
        # We must check if result_node is not None before trying to access it.
        if result_node and 'actual' in result_node:
            return f"Successfully logged entry for '{result_node['actual']}'"
        else:
            print("!!! NEO4J WRITE FAILED: The Cypher query did not return the expected node.")
            return "Failed to log entry to Neo4j."
    driver.close()

# --- Private Cypher Transaction Function ---
def _create_log_entry(tx, log_data: dict):
    """
    A private function that runs the Cypher query to create nodes and relationships.
    This function now safely handles the query result.
    """
    query = (
        """
        MERGE (u:User {id: $userId})
        MERGE (d:Day {date: $day})
        MERGE (u)-[:HAS_DAY]->(d)
        MERGE (tc:TimeChunk {id: $timeChunkId})
        MERGE (d)-[:HAS_CHUNK]->(tc)

        CREATE (a:Actual {
            activity: $actual,
            intention: $intention,
            feeling: $feeling,
            brainFog: $brainFog,
            isValuableDetour: $isValuableDetour,
            inventoryNote: $inventoryNote
        })
        CREATE (r:Reflection {text: $reflection})

        MERGE (tc)-[:RECORDED]->(a)
        MERGE (a)-[:HAS_REFLECTION]->(r)

        RETURN a
        """
    )
    result = tx.run(query,
                    userId="default_user",
                    day=log_data.get('day'),
                    timeChunkId=log_data.get('timeChunk'),
                    intention=log_data.get('intention'),
                    actual=log_data.get('actual'),
                    feeling=log_data.get('feeling'),
                    brainFog=log_data.get('brainFog'),
                    isValuableDetour=log_data.get('isValuableDetour'),
                    inventoryNote=log_data.get('inventoryNote'),
                    reflection=log_data.get('reflection')
                   )
    
    record = result.single()
    if record:
        return record.get('a')
    return None

