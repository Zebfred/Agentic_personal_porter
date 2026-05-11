import os
import logging
from typing import List, Dict
from src.database.neo4j_client import get_driver
from src.agents.gtky_base_classifier import GTKYBaseClassifier

# Configure logging to monitor our "Librarian"
logger = logging.getLogger(__name__)

class GTKYLibrarian(GTKYBaseClassifier):
    """
    The Meticulous Analyst responsible for synchronizing 
    Hero Artifacts (Origin and Intent) with the Graph.
    """
    def __init__(self):
        super().__init__()
        self.driver = get_driver()

    def hard_reset_identity_graph(self):
        """
        Wipes existing identity nodes for a clean start.
        CAUTION: This specifically targets Epoch, Quest, and Intent nodes.
        """
        with self.driver.session() as session:
            session.run("MATCH (n) WHERE n:Epoch OR n:Quest OR n:Intent OR n:Principle DETACH DELETE n")
        logger.info("♻️ Identity Graph nodes wiped for fresh ingestion.")

    def ingest_hero_origin(self, username: str):
        """Maps hero_origin to (Hero)-[:LIVED_THROUGH]->(Epoch) structure."""
        data = self._load_artifact("hero_origin")
        if not data: return

        with self.driver.session() as session:
            for epoch in data['origin_story']['epochs']:
                # Skip empty epochs if they haven't been authored yet
                if not epoch['name']: continue
                
                session.run("""
                    MERGE (h:Hero {hero: $username})
                    MERGE (e:Epoch {name: $name})
                    SET e.timeframe = $timeframe
                    MERGE (h)-[:LIVED_THROUGH]->(e)
                    WITH e
                    UNWIND $experiences AS exp
                    MERGE (x:Experience {title: exp.title})
                    SET x.description = exp.description
                    MERGE (e)-[:CONTAINS]->(x)
                """, name=epoch['name'], timeframe=epoch['timeframe'], experiences=epoch['experiences'], username=username)
        logger.info("✅ Hero Origin artifacts archived in Graph.")

    def ingest_hero_intent(self, username: str):
        """Maps hero_ambition principles and goals as graph anchors."""
        data = self._load_artifact("hero_ambition")
        if not data: return

        with self.driver.session() as session:
            # Ingest Principles
            for principle in data['Principles']:
                session.run("""
                    MATCH (h:Hero {hero: $username})
                    MERGE (p:Principle {text: $text})
                    MERGE (h)-[:GUIDED_BY]->(p)
                """, text=principle, username=username)

            # Ingest Specific Intents (Social, Career, etc.)
            for item in data['Intent']:
                for category, details in item.items():
                    # Handle both list and string detail types from your draft
                    description = ", ".join(details) if isinstance(details, list) else details
                    session.run("""
                        MATCH (h:Hero {hero: $username})
                        MERGE (i:Intent {category: $category})
                        SET i.description = $description
                        MERGE (h)-[:ASPIRES_TO]->(i)
                    """, category=category, description=description, username=username)
        logger.info("🎯 Hero Intent anchors synchronized.")

    def classify_daily_batch(self, daily_events: List[Dict], username: str = "system") -> List[Dict]:
        """
        Phase 2: Reads a day's batch of raw events, bundles them with Hero Context,
        and uses LLM classification to mint \"Golden Objects\".
        """
        return self._classify_batch(
            events=daily_events,
            username=username,
            agent_role="Librarian",
            time_context="daily",
            log_emoji="🧠"
        )

    def run_full_sync(self, username: str):
        """The primary workflow for the Friday deadline."""
        print("🚀 Librarian starting Identity Synchronization...")
        self.hard_reset_identity_graph()
        self.ingest_hero_origin(username)
        self.ingest_hero_intent(username)
        print("✨ Synchronization Complete. Your Graph is now grounded in your Sovereign Context.")

if __name__ == "__main__":
    librarian = GTKYLibrarian()
    hero = os.environ.get("HERO_NAME", "Hero")
    librarian.run_full_sync(hero)