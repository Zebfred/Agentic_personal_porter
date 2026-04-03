import os
import json
import logging
import re
from typing import List, Dict, Any
from pydantic import BaseModel, SecretStr
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
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
        """Maps hero_origin.json to (Hero)-[:LIVED_THROUGH]->(Epoch) structure."""
        data = self._load_json("hero_origin.json")
        if not data: return

        with self.driver.session() as session:
            for epoch in data['origin_story']['epochs']:
                # Skip empty epochs if they haven't been authored yet
                if not epoch['name']: continue
                
                session.run("""
                    MERGE (h:Hero {name: $hero_name})
                    MERGE (e:Epoch {name: $name})
                    SET e.timeframe = $timeframe
                    MERGE (h)-[:LIVED_THROUGH]->(e)
                    WITH e
                    UNWIND $experiences AS exp
                    MERGE (x:Experience {title: exp.title})
                    SET x.description = exp.description
                    MERGE (e)-[:CONTAINS]->(x)
                """, name=epoch['name'], timeframe=epoch['timeframe'], experiences=epoch['experiences'], hero_name=os.environ.get("HERO_NAME", "Hero"))
        logger.info("✅ Hero Origin artifacts archived in Graph.")

    def ingest_hero_intent(self):
        """Maps hero_ambition.json principles and goals as graph anchors."""
        data = self._load_json("hero_ambition.json")
        if not data: return

        with self.driver.session() as session:
            # Ingest Principles
            for principle in data['Principles']:
                session.run("""
                    MATCH (h:Hero {name: $hero_name})
                    MERGE (p:Principle {text: $text})
                    MERGE (h)-[:GUIDED_BY]->(p)
                """, text=principle, hero_name=os.environ.get("HERO_NAME", "Hero"))

            # Ingest Specific Intents (Social, Career, etc.)
            for item in data['Intent']:
                for category, details in item.items():
                    # Handle both list and string detail types from your draft
                    description = ", ".join(details) if isinstance(details, list) else details
                    session.run("""
                        MATCH (h:Hero {name: $hero_name})
                        MERGE (i:Intent {category: $category})
                        SET i.description = $description
                        MERGE (h)-[:ASPIRES_TO]->(i)
                    """, category=category, description=description, hero_name=os.environ.get("HERO_NAME", "Hero"))
        logger.info("🎯 Hero Intent anchors synchronized.")

    def classify_daily_batch(self, daily_events: List[Dict]) -> List[Dict]:
        """
        Phase 2: Reads a day's batch of raw events, bundles them with Hero Context,
        and uses LLM classification to mint \"Golden Objects\".
        Processes in chunks of 10 to avoid token and json formatting issues.
        """
        # Load Contexts
        origin_ctx = self._load_json("hero_origin.json")
        ambition_ctx = self._load_json("hero_ambition.json")
        
        # System Prompt
        system_prompt = """You are the GTKY Librarian Agent. Your duty is to review the user's raw Google Calendar events for the day 
and rigidly classify them into "Golden Objects" based on the user's Origin Story and Ambitions.

Context of the Hero:
Origin: {origin}
Ambitions/Intent: {ambition}

Given a list of JSON calendar events, analyze each and output exactly a valid JSON array of objects with the following identical schema.
If an event falls under a specific ambition (e.g., "Career Goal"), use that as the 'pillar'. If not, categorize it broadly (e.g., "Social", "Rest", "Maintenance").

Schema per object:
{{
  "gcal_id": "string (MUST MATCH the input gcal_id exactly)",
  "title": "string",
  "start": "string",
  "duration_minutes": int,
  "record_type": "Actual",
  "pillar": "string (Must map to an ambition category or generic)",
  "subcategory": "string (More detailed description)",
  "is_valuable_detour": boolean (True if it was an unplanned but positive diversion)
}}

Output ONLY the raw JSON array. No markdown blocks, no chat formatting.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Here is the raw batch of calendar events:\n{events_batch}")
        ])
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.error("No GROQ_API_KEY found in environment.")
            return []
            
        llm = ChatGroq(
            api_key=SecretStr(api_key),
            model="llama3-70b-8192",
            temperature=0.0
        )
        
        chain = prompt | llm
        
        golden_objects = []
        chunk_size = 10
        
        for i in range(0, len(daily_events), chunk_size):
            chunk = daily_events[i:i + chunk_size]
            events_subset = []
            for ev in chunk:
                # Pre-calculate duration since raw GCal might lack it
                duration = 60
                # Simplification: we forward 'start', 'end', 'summary', 'gcal_id'
                events_subset.append({
                    "gcal_id": ev.get("gcal_id"),
                    "summary": ev.get("summary"),
                    "start": ev.get("start"),
                    "end": ev.get("end")
                })
                
            logger.info(f"🧠 Librarian processing batch {i} to {i + len(chunk)}...")
            
            try:
                response = chain.invoke({
                    "origin": json.dumps(origin_ctx),
                    "ambition": json.dumps(ambition_ctx),
                    "events_batch": json.dumps(events_subset, indent=2)
                })
                
                # Cleanup the markdown if it hallucinates it
                raw_json = response.content.strip()
                raw_json = re.sub(r'^```json|^```', '', raw_json, flags=re.MULTILINE)
                raw_json = raw_json.strip('`').strip()
                
                parsed_objects = json.loads(raw_json)
                
                # Validate and append
                if isinstance(parsed_objects, list):
                    for obj in parsed_objects:
                        if "gcal_id" in obj:
                            golden_objects.append(obj)
            except Exception as e:
                logger.error(f"❌ Failed to classify chunk {i}: {e}")
                
        return golden_objects

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