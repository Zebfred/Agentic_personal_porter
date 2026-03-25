import json
import sys
import os
from neo4j import GraphDatabase
from pathlib import Path

root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.config import NeoConfig
from src.database.mongo_storage import SovereignMongoStorage

# --- Configuration ---
driver = GraphDatabase.driver(NeoConfig.NEO4J_URI, auth=(NeoConfig.NEO4J_USER, NeoConfig.NEO4J_PASS))
mongo_storage = SovereignMongoStorage()



def flatten_intents(raw_intents):
    """
    Flattens the nested Intent structures from hero_ambition.json 
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

def inject_hero_data(hero_name=None):
    if hero_name is None:
        hero_name = os.environ.get("HERO_NAME", "Hero")
    """Reads the JSON and runs the Cypher queries to build the Hero foundation."""
    
    ambition_data = mongo_storage.get_hero_artifact('hero_ambition.json')
    if not ambition_data:
        print("Error: hero_ambition.json not found in MongoDB.")
        return
    principles = ambition_data.get("Principles", [])
    raw_intents = ambition_data.get("Intent", [])
    flat_intents = flatten_intents(raw_intents)
    #Might be better way to parse
    #flat_intents = flatten_intents(ambition_data.get("Intent", []))

    
    origin_data = mongo_storage.get_hero_artifact('hero_origin.json')
    if not origin_data:
        print("Error: hero_origin.json not found in MongoDB.")
        return
    raw_epochs = origin_data.get("origin_story", {}).get("epochs", [])
    epochs_data, experiences_data = process_epochs(raw_epochs)
    

    # 3. Cypher Queries
    merge_hero_and_principles_query = """
    MERGE (h:Hero {name: $hero_name})
    MERGE (h)-[:HAS_ARTIFACTS]->(art:Artifacts {name: "Hero Artifacts"})
    WITH art
    UNWIND $principles AS principle_text
    MERGE (p:Principle {text: principle_text})
    MERGE (art)-[:GUIDED_BY]->(p)
    """

    merge_intents_query = """
    MATCH (h:Hero {name: $hero_name})-[:HAS_ARTIFACTS]->(art:Artifacts)
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
    MATCH (h:Hero {name: $hero_name})-[:HAS_ARTIFACTS]->(art:Artifacts)

    // Create the Origin node and link it to Artifacts
    MERGE (o:Origin {hero_name: $hero_name, name: "Hero_Origins"})
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
        session.run(merge_hero_and_principles_query, hero_name=hero_name, principles=principles)
        print(f"✨ Fabulously injected {len(principles)} Principles!")
        
        session.run(merge_intents_query, hero_name=hero_name, intents=flat_intents)
        print(f"✨ Gorgeously injected {len(flat_intents)} Intents!")

        session.run(merge_epochs_query, hero_name=hero_name, epochs=epochs_data)
        print(f"✨ Mapped {len(epochs_data)} Life Epochs!")

        session.run(merge_experiences_query, experiences=experiences_data)
        print(f"✨ Planted {len(experiences_data)} Experiences and Candidates!")

if __name__ == "__main__":
    try:
        inject_hero_data()
    finally:
        driver.close()