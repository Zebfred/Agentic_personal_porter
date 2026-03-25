from .connection import get_driver

import os

def get_valuable_detours(user_name=None):
    if user_name is None:
        user_name = os.environ.get("HERO_NAME", "Hero")
    """
    Retrieves all 'Valuable Detours' (Achievements) logged for the given Hero.
    Returns a list of dictionaries with inventoryNote and the original Activity title.
    """
    driver = get_driver()
    query = """
    MATCH (u:Hero {name: $userName})-[:HAS_ACHIEVEMENT]->(ach:Achievement)
    MATCH (a:Actual)-[:ACHIEVED]->(ach)
    RETURN ach.description AS inventoryNote, a.activity AS title, ach.timestamp AS timestamp
    ORDER BY ach.timestamp DESC
    """
    with driver.session() as session:
        result = session.run(query, userName=user_name)
        detours = [{"inventoryNote": record["inventoryNote"], "title": record["title"], "timestamp": str(record["timestamp"])} for record in result]
    driver.close()
    return detours

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
