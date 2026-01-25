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
    Enhanced function that creates nodes and relationships with meaningful connections.
    
    Creates:
    - Basic structure: User -> Day -> TimeChunk -> Actual -> Reflection
    - Intention node linked to Actual
    - Achievement node if valuable detour
    - State nodes for affected states (emotional, energy, time-based)
    - Goal relationships if intention matches a goal pattern
    """
    intention_text = log_data.get('intention', '')
    actual_text = log_data.get('actual', '')
    feeling = log_data.get('feeling', '')
    brain_fog = log_data.get('brainFog', 0)
    is_valuable_detour = log_data.get('isValuableDetour', False)
    inventory_note = log_data.get('inventoryNote', '')
    
    # Determine time of day from timeChunk for state tracking
    time_chunk = log_data.get('timeChunk', '')
    time_of_day = _extract_time_of_day(time_chunk)
    
    query = (
        """
        // Find or create user
        MERGE (u:User {id: $userId})
        
        // Create day and link to user
        MERGE (d:Day {date: $day})
        MERGE (u)-[:HAS_DAY]->(d)
        
        // Create time chunk
        MERGE (tc:TimeChunk {id: $timeChunkId})
        MERGE (d)-[:HAS_CHUNK]->(tc)
        
        // Create Intention node
        CREATE (int:Intention {
            description: $intention,
            timestamp: datetime()
        })
        MERGE (tc)-[:INTENDED]->(int)
        
        // Create Actual node
        CREATE (a:Actual {
            activity: $actual,
            feeling: $feeling,
            brainFog: $brainFog,
            isValuableDetour: $isValuableDetour,
            inventoryNote: $inventoryNote,
            timestamp: datetime()
        })
        MERGE (tc)-[:RECORDED]->(a)
        
        // Link Actual to Intention
        MERGE (int)-[:BECAME]->(a)
        
        // Create Reflection
        CREATE (r:Reflection {
            text: $reflection,
            timestamp: datetime()
        })
        MERGE (a)-[:HAS_REFLECTION]->(r)
        
        // Create Achievement if valuable detour
        WITH a, u, int, r, $isValuableDetour as isDetour, $inventoryNote as note
        WHERE isDetour = true AND note IS NOT NULL AND note <> ''
        CREATE (ach:Achievement {
            description: note,
            value: 'positive',
            timestamp: datetime()
        })
        MERGE (a)-[:ACHIEVED]->(ach)
        MERGE (u)-[:HAS_ACHIEVEMENT]->(ach)
        
        // Create Affected States
        WITH a, u, int, r, $feeling as feeling, $brainFog as fog, $timeOfDay as tod
        CREATE (emState:State {
            type: 'emotional',
            value: feeling,
            timestamp: datetime()
        })
        CREATE (enState:State {
            type: 'energy',
            value: toString(100 - toInteger(fog)),
            timestamp: datetime()
        })
        CREATE (timeState:State {
            type: 'time_of_day',
            value: tod,
            timestamp: datetime()
        })
        MERGE (a)-[:AFFECTED_BY]->(emState)
        MERGE (a)-[:AFFECTED_BY]->(enState)
        MERGE (a)-[:AFFECTED_BY]->(timeState)
        
        // Try to link to existing Goal if intention matches goal pattern
        // (This is a simple pattern match - can be enhanced with AI)
        WITH a, u, int, $intention as intentionText
        WHERE intentionText IS NOT NULL AND intentionText <> ''
        OPTIONAL MATCH (g:Goal)
        WHERE toLower(g.description) CONTAINS toLower(intentionText) 
           OR toLower(intentionText) CONTAINS toLower(g.description)
        WITH a, u, int, g
        WHERE g IS NOT NULL
        MERGE (int)-[:TARGETS]->(g)
        MERGE (a)-[:ALIGNED_WITH]->(g)
        
        RETURN a, int, r
        """
    )
    
    result = tx.run(query,
                    userId="default_user",
                    day=log_data.get('day'),
                    timeChunkId=log_data.get('timeChunk'),
                    intention=intention_text,
                    actual=actual_text,
                    feeling=feeling,
                    brainFog=int(brain_fog) if brain_fog else 0,
                    isValuableDetour=is_valuable_detour,
                    inventoryNote=inventory_note,
                    reflection=log_data.get('reflection', ''),
                    timeOfDay=time_of_day
                   )
    
    record = result.single()
    if record:
        return record.get('a')
    return None


# --- Goal Management Functions ---

def create_goal(user_id: str, description: str, category: str = "general", 
                priority: str = "medium", timeframe: str = "ongoing") -> dict:
    """
    Create a Goal node in Neo4j.
    
    Args:
        user_id: User identifier
        description: Goal description
        category: Goal category (e.g., "work", "health", "learning")
        priority: Priority level ("low", "medium", "high")
        timeframe: Timeframe ("short-term", "mid-term", "long-term", "ongoing")
        
    Returns:
        Created goal node or None if error
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.write_transaction(_create_goal_tx, user_id, description, 
                                          category, priority, timeframe)
    driver.close()
    return result


def _create_goal_tx(tx, user_id: str, description: str, category: str, 
                   priority: str, timeframe: str):
    """Transaction function to create a goal."""
    query = (
        """
        MATCH (u:User {id: $userId})
        CREATE (g:Goal {
            description: $description,
            category: $category,
            priority: $priority,
            timeframe: $timeframe,
            createdAt: datetime(),
            status: 'active'
        })
        MERGE (u)-[:HAS_GOAL]->(g)
        RETURN g
        """
    )
    result = tx.run(query, userId=user_id, description=description, 
                   category=category, priority=priority, timeframe=timeframe)
    record = result.single()
    return record.get('g') if record else None


# --- Query Functions for Insights ---

def get_user_patterns(user_id: str) -> list:
    """
    Find patterns in user's intentions vs actuals.
    
    Args:
        user_id: User identifier
        
    Returns:
        List of pattern dictionaries
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.read_transaction(_get_patterns_tx, user_id)
    driver.close()
    return result


def _get_patterns_tx(tx, user_id: str):
    """Transaction to find patterns."""
    query = (
        """
        MATCH (u:User {id: $userId})-[:HAS_DAY]->(d:Day)-[:HAS_CHUNK]->(tc:TimeChunk)
        MATCH (tc)-[:INTENDED]->(int:Intention)-[:BECAME]->(a:Actual)
        WITH int.description as intention, a.activity as actual, count(*) as frequency
        WHERE frequency > 1
        RETURN intention, actual, frequency
        ORDER BY frequency DESC
        LIMIT 10
        """
    )
    result = tx.run(query, userId=user_id)
    return [{"intention": record["intention"], 
             "actual": record["actual"], 
             "frequency": record["frequency"]} 
            for record in result]


def get_goal_progress(user_id: str, goal_id: str = None) -> dict:
    """
    Track progress toward goals.
    
    Args:
        user_id: User identifier
        goal_id: Optional specific goal ID
        
    Returns:
        Progress information
    """
    driver = get_driver()
    with driver.session() as session:
        if goal_id:
            result = session.read_transaction(_get_specific_goal_progress_tx, user_id, goal_id)
        else:
            result = session.read_transaction(_get_all_goals_progress_tx, user_id)
    driver.close()
    return result


def _get_specific_goal_progress_tx(tx, user_id: str, goal_id: str):
    """Get progress for a specific goal."""
    query = (
        """
        MATCH (u:User {id: $userId})-[:HAS_GOAL]->(g:Goal {id: $goalId})
        OPTIONAL MATCH (int:Intention)-[:TARGETS]->(g)
        OPTIONAL MATCH (int)-[:BECAME]->(a:Actual)-[:ALIGNED_WITH]->(g)
        RETURN g.description as goal,
               count(DISTINCT int) as intentions_count,
               count(DISTINCT a) as aligned_actions_count
        """
    )
    result = tx.run(query, userId=user_id, goalId=goal_id)
    record = result.single()
    return dict(record) if record else {}


def _get_all_goals_progress_tx(tx, user_id: str):
    """Get progress for all goals."""
    query = (
        """
        MATCH (u:User {id: $userId})-[:HAS_GOAL]->(g:Goal)
        OPTIONAL MATCH (int:Intention)-[:TARGETS]->(g)
        OPTIONAL MATCH (int)-[:BECAME]->(a:Actual)-[:ALIGNED_WITH]->(g)
        RETURN g.description as goal,
               g.status as status,
               count(DISTINCT int) as intentions_count,
               count(DISTINCT a) as aligned_actions_count
        ORDER BY aligned_actions_count DESC
        """
    )
    result = tx.run(query, userId=user_id)
    return [dict(record) for record in result]


def get_state_correlations(user_id: str) -> list:
    """
    Find correlations between states and actions.
    
    Args:
        user_id: User identifier
        
    Returns:
        List of correlation patterns
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.read_transaction(_get_state_correlations_tx, user_id)
    driver.close()
    return result


def _get_state_correlations_tx(tx, user_id: str):
    """Get state correlations."""
    query = (
        """
        MATCH (u:User {id: $userId})-[:HAS_DAY]->(d:Day)-[:HAS_CHUNK]->(tc:TimeChunk)
        MATCH (tc)-[:RECORDED]->(a:Actual)-[:AFFECTED_BY]->(s:State)
        WITH s.type as stateType, s.value as stateValue, a.activity as activity, count(*) as frequency
        WHERE frequency > 1
        RETURN stateType, stateValue, activity, frequency
        ORDER BY frequency DESC
        LIMIT 20
        """
    )
    result = tx.run(query, userId=user_id)
    return [dict(record) for record in result]


def _extract_time_of_day(time_chunk_id: str) -> str:
    """
    Extract time of day category from time chunk ID.
    
    Args:
        time_chunk_id: Time chunk identifier
        
    Returns:
        Time of day category string
    """
    time_chunk_map = {
        'late-night': 'night',
        'early-morning': 'morning',
        'late-morning': 'morning',
        'afternoon': 'afternoon',
        'evening': 'evening',
        'early-night': 'night'
    }
    return time_chunk_map.get(time_chunk_id, 'unknown')

