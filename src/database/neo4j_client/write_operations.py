from .connection import get_driver

def log_to_neo4j(log_data: dict) -> str:
    """
    Logs a complete journal entry to the Neo4j database.
    Returns a confirmation message.
    """
    driver = get_driver()
    with driver.session() as session:
        result_node = session.execute_write(_create_log_entry, log_data)
        
        # another potential fix
        # We must check if result_node is not None before trying to access it.
        if result_node and 'activity' in result_node:
            return f"Successfully logged entry for '{result_node['activity']}'"
        else:
            print("!!! NEO4J WRITE FAILED: The Cypher query did not return the expected node.")
            return "Failed to log entry to Neo4j."
    driver.close()

def _create_log_entry(tx, log_data: dict):
    """
    Enhanced function that creates nodes and relationships with meaningful connections.
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
        // Find or create Hero
        MERGE (u:Hero {name: $userName})
        
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
        FOREACH (x IN CASE WHEN isDetour = true AND note IS NOT NULL AND note <> '' THEN [1] ELSE [] END |
            CREATE (ach:Achievement {
                description: note,
                value: 'positive',
                timestamp: datetime()
            })
            MERGE (a)-[:ACHIEVED]->(ach)
            MERGE (u)-[:HAS_ACHIEVEMENT]->(ach)
        )
        
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
        WITH a, u, int, r, $intention as intentionText
        OPTIONAL MATCH (g:Goal)
        WHERE (intentionText IS NOT NULL AND intentionText <> '') AND (
              toLower(g.description) CONTAINS toLower(intentionText) 
           OR toLower(intentionText) CONTAINS toLower(g.description)
        )
        WITH a, u, int, r, g
        FOREACH (x IN CASE WHEN g IS NOT NULL THEN [1] ELSE [] END |
            MERGE (int)-[:TARGETS]->(g)
            MERGE (a)-[:ALIGNED_WITH]->(g)
        )
        
        RETURN a, int, r
        """
        
    )
    
    result = tx.run(query,
                    userName=os.environ.get("HERO_NAME", "Hero"),
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

def create_identity_graph(user_id, origin_story, ambitions):
    """
    Parses the GTKY Agent's output to build the Identity Graph.
    Uses MERGE to ensure idempotency.
    """
    driver = get_driver()
    query = """
    MATCH (u:User {id: $user_id})
    
    // 1. Map the Origin Story (Who you are)
    FOREACH (trait IN $origin_story.traits |
        MERGE (i:Identity {name: trait.name})
        SET i.category = trait.category
        MERGE (u)-[:DEFINES_IDENTITY]->(i)
    )
    
    // 2. Map Future Ambitions (Where you are going)
    FOREACH (quest IN $ambitions |
        MERGE (a:Ambition {name: quest.title})
        SET a.target_date = quest.target_date,
            a.status = 'ACTIVE'
        MERGE (u)-[:HAS_AMBITION]->(a)
    )
    
    // 3. Link Ambitions to specific Life Pillars if known
    WITH u
    MATCH (u)-[:HAS_AMBITION]->(a:Ambition), (p:Pillar)
    WHERE a.name CONTAINS p.name // Simple heuristic for now
    MERGE (a)-[:SUPPORTS_PILLAR]->(p)
    """

    # Execute query with parameters
    with driver.session() as session:
        session.run(query, user_id=user_id, origin_story=origin_story, ambitions=ambitions)
    driver.close()
    user_id_graph = f"Identity graph created/updated successfully for user {user_id}"
    print(user_id_graph)
    return user_id_graph

def create_goal(user_id: str, description: str, category: str = "general", 
                priority: str = "medium", timeframe: str = "ongoing") -> dict:
    """
    Create a Goal node in Neo4j.
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

def _extract_time_of_day(time_chunk_id: str) -> str:
    """
    Extract time of day category from time chunk ID.
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
