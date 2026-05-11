import logging
from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import json
import sys
import os
from pathlib import Path

from src.database.mongo_storage import SovereignMongoStorage
from src.database.neo4j_client.connection import get_driver

# --- Configuration ---
driver = get_driver()
mongo_storage = SovereignMongoStorage()

def get_or_create_time_chunk(driver, target_datetime, username="system"):
    """
    Dynamic generation of the Week -> Day -> TimeChunk hierarchy under TimeHub.
    Enforces UTC to ensure consistent chunk generation.
    """
    from datetime import timezone
    
    # Enforce UTC
    if target_datetime.tzinfo is None:
        dt = target_datetime.replace(tzinfo=timezone.utc)
    else:
        dt = target_datetime.astimezone(timezone.utc)
        
    chunk_index = (dt.hour // 4) + 1
    
    year, week, _ = dt.isocalendar()
    day_of_week = dt.weekday() + 1
    
    week_id = f"{year}-W{week:02d}"
    day_id = f"{week_id}-D{day_of_week}"
    chunk_id = f"{day_id}-C{chunk_index}"
    
    query = """
    MATCH (h:Hero {hero: $username})-[:ADHERES_TO]->(t_hub:TimeHub)
    
    // Week
    MERGE (t_hub)-[:HAS_WEEK]->(w:Week {id: $week_id, year: $year, week: $week})
    
    // Day
    MERGE (w)-[:HAS_DAY]->(d:Day {id: $day_id, day_of_week: $day_of_week})
    
    // TimeChunk (The specific 4-hour block)
    MERGE (d)-[:HAS_TIME_CHUNK]->(tc:TimeChunk {id: $chunk_id, chunk_index: $chunk_index})
    
    RETURN tc.id AS time_chunk_id
    """
    
    try:
        with driver.session() as session:
            result = session.run(query, username=username, week_id=week_id, year=year, week=week, 
                                 day_id=day_id, day_of_week=day_of_week, 
                                 chunk_id=chunk_id, chunk_index=chunk_index)
            record = result.single()
            return record["time_chunk_id"] if record else None
    except Exception as e:
        logger.info(f"Time Structure Generation Error: {e}")
        return None

def flatten_intents(raw_intents):
    """
    Flattens the nested Intent structures from hero_ambition 
    into a clean list of dictionaries for Cypher.
    """
    flattened = []
    for intent_dict in raw_intents:
        for main_category, value in intent_dict.items():
            
            # Case 1: Simple String (e.g., Career Goal, Health Goal)
            if isinstance(value, str):
                flattened.append({
                    "category": main_category, 
                    "description": value, 
                    "parent_category": "None"
                })
                
            # Case 2: List of items
            elif isinstance(value, list):
                # Subcase A: List of strings (e.g., Social Goal)
                if all(isinstance(i, str) for i in value):
                    flattened.append({
                        "category": main_category, 
                        "description": " ".join(value), 
                        "parent_category": "None"
                    })
                # Subcase B: List of dictionaries (e.g., Loved ones)
                elif all(isinstance(i, dict) for i in value):

                    flattened.append({"category": main_category, "description": "Sub-goals contained within.", "parent_category": "None"})

                    for sub_dict in value:
                        for sub_cat, sub_desc in sub_dict.items():
                            flattened.append({
                                "category": sub_cat, 
                                "description": sub_desc, 
                                "parent_category": main_category
                            })
    return flattened

def process_epochs(raw_epochs):
    """
    Parses the epochs and cleanly separates actual experiences 
    from 'experience candidates' (the blank slates for Mach 3).
    """
    processed_epochs = []
    processed_experiences = []

    for epoch in raw_epochs:
        epoch_name = epoch.get("name", "Unknown Epoch")
        timeframe = epoch.get("timeframe", "Unknown Timeframe")
        
        processed_epochs.append({
            "name": epoch_name,
            "timeframe": timeframe
        })

        # 1. Process actual logged experiences
        for exp in epoch.get("experiences", []):
            title = exp.get("title", "").strip()
            desc = exp.get("description", "").strip()
            
            # If the title is blank, we can treat it as an empty slot for the agent
            status = "Logged" if desc else "Needs_Detail"
            
            # Only append if there's actually a title or a description
            if title or desc:
                processed_experiences.append({
                    "epoch_name": epoch_name,
                    "title": title if title else "Untitled Memory",
                    "description": desc,
                    "status": status
                })

        # 2. Process experience candidates (ideas waiting to be fleshed out)
        for candidate in epoch.get("experience candidate", []):
            if isinstance(candidate, str) and candidate.strip():
                processed_experiences.append({
                    "epoch_name": epoch_name,
                    "title": candidate.strip(),
                    "description": "", # Empty, waiting for you!
                    "status": "Candidate"
                })

    return processed_epochs, processed_experiences

import os

def inject_hero_data(username=None):
    if username is None:
        username = os.environ.get("HERO_NAME", "Hero")
    """Reads the JSON and runs the Cypher queries to build the Hero foundation."""
    
    ambition_data = mongo_storage.get_hero_artifact('hero_ambition', username)
    if not ambition_data:
        logger.info("Error: hero_ambition not found in MongoDB.")
        return
    principles = ambition_data.get("Principles", [])
    raw_intents = ambition_data.get("Intent", [])
    flat_intents = flatten_intents(raw_intents)
    #Might be better way to parse
    #flat_intents = flatten_intents(ambition_data.get("Intent", []))

    
    origin_data = mongo_storage.get_hero_artifact('hero_origin', username)
    if not origin_data:
        logger.info("Error: hero_origin not found in MongoDB.")
        return
    raw_epochs = origin_data.get("origin_story", {}).get("epochs", [])
    epochs_data, experiences_data = process_epochs(raw_epochs)
    

    # 3. Cypher Queries
    merge_hero_and_principles_query = """
    MERGE (h:Hero {hero: $username})
    
    // Establish Primary Branches
    MERGE (h)-[:DIRECTED_BY]->(art:Artifacts {name: "Hero Artifacts"})
    MERGE (h)-[:ADHERES_TO]->(p_hub:PillarsHub {name: "Life Pillars"})
    MERGE (h)-[:ADHERES_TO]->(t_hub:TimeHub {name: "Time Structure"})
    
    WITH h, art, p_hub
    UNWIND $principles AS principle_text
    MERGE (p:Principle {text: principle_text})
    MERGE (art)-[:GUIDED_BY]->(p)
    """

    # Pillars generation
    category_map_data = mongo_storage.get_hero_artifact('category_mapping', username)
    pillars_list = []
    if category_map_data and "intent_to_actual_mapping" in category_map_data:
        unique_pillars = set(category_map_data["intent_to_actual_mapping"].keys()).union(
            set(category_map_data["intent_to_actual_mapping"].values())
        )
        pillars_list = list(unique_pillars)
    else:
        # Fallback to constants
        from src.constants import ACTUAL_CATEGORY_MAPPING
        if "intent_to_actual_mapping" in ACTUAL_CATEGORY_MAPPING:
            unique_pillars = set(ACTUAL_CATEGORY_MAPPING["intent_to_actual_mapping"].keys()).union(
                set(ACTUAL_CATEGORY_MAPPING["intent_to_actual_mapping"].values())
            )
            pillars_list = list(unique_pillars)

    merge_pillars_query = """
    MATCH (h:Hero {hero: $username})-[:ADHERES_TO]->(p_hub:PillarsHub)
    UNWIND $pillars AS pillar_name
    MERGE (p:Pillar {name: pillar_name})
    MERGE (p_hub)-[:HAS_PILLAR]->(p)
    """

    merge_intents_query = """
    MATCH (h:Hero {hero: $username})-[:DIRECTED_BY]->(art:Artifacts)
    UNWIND $intents AS intent
    MERGE (i:Intent {category: intent.category})
    SET i.description = intent.description,
        i.parent_category = intent.parent_category
    
    // Link top-level intents directly to the Artifacts node
    FOREACH (_ IN CASE WHEN intent.parent_category = 'None' THEN [1] ELSE [] END |
        MERGE (art)-[:HAS_INTENT]->(i)
    )
    
    // Link sub-intents (like Romantic Goal) to their parent (Loved ones)
    FOREACH (_ IN CASE WHEN intent.parent_category <> 'None' THEN [1] ELSE [] END |
        MERGE (parent:Intent {category: intent.parent_category})
        MERGE (parent)-[:HAS_SUB_INTENT]->(i)
    )
    """

    # Timeline & Memories
    merge_epochs_query = """
    MATCH (h:Hero {hero: $username})-[:DIRECTED_BY]->(art:Artifacts)

    // Create the Origin node and link it to Artifacts
    MERGE (o:Origin {hero_name: $username, name: "Hero_Origins"})
    MERGE (art)-[:HAS_ORIGIN]->(o)
    WITH o

    // Now attach the Epochs to the Origin node
    UNWIND $epochs AS epoch
    MERGE (e:Epoch {name: epoch.name})
    SET e.timeframe = epoch.timeframe
    MERGE (o)-[:HAS_EPOCH]->(e)
    """
    merge_experiences_query = """
    UNWIND $experiences AS exp
    MATCH (e:Epoch {name: exp.epoch_name})
    MERGE (x:Experience {title: exp.title, epoch_name: exp.epoch_name})
    SET x.description = exp.description,
        x.status = exp.status
    MERGE (e)-[:HAS_EXPERIENCE]->(x)
    """

    # --- 4. Execute in Neo4j ---
    with driver.session() as session:
        session.run(merge_hero_and_principles_query, username=username, principles=principles)
        logger.info(f"✨ Fabulously injected {len(principles)} Principles and Primary Branches!")

        if pillars_list:
            session.run(merge_pillars_query, username=username, pillars=pillars_list)
            logger.info(f"✨ Dynamically injected {len(pillars_list)} Life Pillars!")
        
        session.run(merge_intents_query, username=username, intents=flat_intents)
        logger.info(f"✨ Gorgeously injected {len(flat_intents)} Intents!")

        session.run(merge_epochs_query, username=username, epochs=epochs_data)
        logger.info(f"✨ Mapped {len(epochs_data)} Life Epochs!")

        session.run(merge_experiences_query, experiences=experiences_data)
        logger.info(f"✨ Planted {len(experiences_data)} Experiences and Candidates!")

if __name__ == "__main__":
    try:
        inject_hero_data()
    finally:
        driver.close()
