import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# --- Database Connection ---
URI = os.getenv("NEO4J_URI")
AUTH_USER = os.getenv("NEO4J_USERNAME")
AUTH_PASS = os.getenv("NEO4J_PASSWORD")

def get_driver():
    """Establishes a connection to the Neo4j database."""
    return GraphDatabase.driver(URI, auth=(AUTH_USER, AUTH_PASS))

# --- User Management Functions ---

def create_user(tx, username, hashed_password):
    """
    Creates a new User node if the username doesn't already exist.
    """
    # First, check if the user already exists
    existing_user = tx.run("MATCH (u:User {username: $username}) RETURN u", username=username).single()
    if existing_user:
        return None # Indicate that the user already exists

    # If not, create the new user
    result = tx.run(
        "CREATE (u:User {username: $username, password: $password}) RETURN u",
        username=username,
        password=hashed_password
    )
    return result.single()[0]

def get_user(tx, username):
    """
    Retrieves a user by their username.
    """
    result = tx.run("MATCH (u:User {username: $username}) RETURN u", username=username)
    record = result.single()
    return record[0] if record else None


# --- Logging Function ---
def log_to_neo4j(log_data: dict, user_id: str) -> str:
    """
    Logs a complete journal entry to the Neo4j database for a specific user.
    Returns a confirmation message.
    """
    driver = get_driver()
    with driver.session() as session:
        result_node = session.write_transaction(_create_log_entry, log_data, user_id)
        
        if result_node and 'activity' in result_node:
            return f"Successfully logged entry for '{result_node['activity']}'"
        else:
            print("!!! NEO4J WRITE FAILED: The Cypher query did not return the expected node.")
            return "Failed to log entry to Neo4j."
    driver.close()

# --- Private Cypher Transaction Function ---
def _create_log_entry(tx, log_data: dict, user_id: str):
    """
    A private function that runs the Cypher query to create nodes and relationships,
    linking them to the specified user.
    """
    query = (
        """
        // Find the user first
        MATCH (u:User {username: $userId})

        // Merge the day and time chunk, linking them to the user
        MERGE (d:Day {date: $day})
        MERGE (u)-[:HAS_DAY]->(d)
        MERGE (tc:TimeChunk {id: $timeChunkId})
        MERGE (d)-[:HAS_CHUNK]->(tc)

        // Create the actual log entry and reflection
        CREATE (a:Actual {
            activity: $actual,
            intention: $intention,
            feeling: $feeling,
            brainFog: $brainFog,
            isValuableDetour: $isValuableDetour,
            inventoryNote: $inventoryNote
        })
        CREATE (r:Reflection {text: $reflection})

        // Link them together
        MERGE (tc)-[:RECORDED]->(a)
        MERGE (a)-[:HAS_REFLECTION]->(r)

        RETURN a
        """
    )
    result = tx.run(query,
                    userId=user_id, # Use the passed-in user_id
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
    return record.get('a') if record else None