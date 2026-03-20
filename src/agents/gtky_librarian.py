import os
import json
import logging
from typing import List, Dict, Any
from src.utils.path_utils import load_env_vars, get_project_root
from src.database.neo4j_client import get_driver

# Configure logging to monitor our "Librarian"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GTKYLibrarian:
    """
    The Meticulous Analyst responsible for synchronizing 
    Hero Artifacts (Origin and Intent) with the Graph.
    """
    def __init__(self):
        load_env_vars()
        self.driver = get_driver()
        self.artifacts_dir = get_project_root() / "data" / "hero_artifacts"

    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Loads artifact JSONs, handling missing files gracefully."""
        file_path = self.artifacts_dir / filename
        if not file_path.exists():
            logger.error(f"❌ Artifact missing: {file_path}")
            return {}
        with open(file_path, 'r') as f:
            return json.load(f)

    def hard_reset_identity_graph(self):
        """
        Wipes existing identity nodes for a clean Mach 2 start.
        CAUTION: This specifically targets Epoch, Quest, and Intent nodes.
        """
        with self.driver.session() as session:
            session.run("MATCH (n) WHERE n:Epoch OR n:Quest OR n:Intent OR n:Principle DETACH DELETE n")
        logger.info("♻️ Identity Graph nodes wiped for fresh ingestion.")

    def ingest_hero_origin(self):
        """Maps hero_origin.json to (User)-[:LIVED_THROUGH]->(Epoch) structure."""
        data = self.load_json("hero_origin.json")
        if not data: return

        with self.driver.session() as session:
            for epoch in data['origin_story']['epochs']:
                # Skip empty epochs if they haven't been authored yet
                if not epoch['name']: continue
                
                session.run("""
                    MERGE (u:User {name: 'Jimmy'})
                    MERGE (e:Epoch {name: $name})
                    SET e.timeframe = $timeframe
                    MERGE (u)-[:LIVED_THROUGH]->(e)
                    WITH e
                    UNWIND $experiences AS exp
                    MERGE (x:Experience {title: exp.title})
                    SET x.description = exp.description
                    MERGE (e)-[:CONTAINS]->(x)
                """, name=epoch['name'], timeframe=epoch['timeframe'], experiences=epoch['experiences'])
        logger.info("✅ Hero Origin artifacts archived in Graph.")

    def ingest_hero_intent(self):
        """Maps hero_intent.json principles and goals as graph anchors."""
        data = self._load_json("hero_intent.json")
        if not data: return

        with self.driver.session() as session:
            # Ingest Principles
            for principle in data['Principles']:
                session.run("""
                    MATCH (u:User {name: 'Jimmy'})
                    MERGE (p:Principle {text: $text})
                    MERGE (u)-[:GUIDED_BY]->(p)
                """, text=principle)

            # Ingest Specific Intents (Social, Career, etc.)
            for item in data['Intent']:
                for category, details in item.items():
                    # Handle both list and string detail types from your draft
                    description = ", ".join(details) if isinstance(details, list) else details
                    session.run("""
                        MATCH (u:User {name: 'Jimmy'})
                        MERGE (i:Intent {category: $category})
                        SET i.description = $description
                        MERGE (u)-[:ASPIRES_TO]->(i)
                    """, category=category, description=description)
        logger.info("🎯 Hero Intent anchors synchronized.")

    def run_full_sync(self):
        """The primary workflow for the Friday deadline."""
        print("🚀 Librarian starting Identity Synchronization...")
        self.hard_reset_identity_graph()
        self.ingest_hero_origin()
        self.ingest_hero_intent()
        print("✨ Synchronization Complete. Your Graph is now grounded in your Sovereign Context.")

if __name__ == "__main__":
    librarian = GTKYLibrarian()
    librarian.run_full_sync()