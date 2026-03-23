import os
import json
import logging
from pydantic import SecretStr
from langchain_groq import ChatGroq
from src.utils.path_utils import load_env_vars, get_project_root
from src.database.neo4j_client import get_driver

# Configure logging
logger = logging.getLogger(__name__)
load_env_vars()

class GTKYBrain:
    """
    The Identity Architect of the Porter.
    Parses the Self-Authoring 'Origin Story' to populate the Identity Graph.
    """
    def __init__(self):
        self.api_key = SecretStr(os.getenv("GROQ_API_KEY"))
        self.llm = ChatGroq(api_key=self.api_key, model_name="groq/llama-3.3-70b-versatile")
        self.origin_file = get_project_root() / "data" / "hero_artifacts" / "hero_origin.json"
        self.driver = get_driver()

    def load_origin_story(self):
        """Loads the JSON structure based on the Self-Authoring Suite."""
        if not os.path.exists(self.origin_file):
            logger.error(f"Origin story missing at {self.origin_file}")
            return None
        with open(self.origin_file, 'r') as f:
            return json.load(f)

    def sync_identity_to_graph(self):
        """Maps Past, Present, and Future Authoring to Neo4j nodes."""
        data = self.load_origin_story()
        if not data: return

        with self.driver.session() as session:
            # 1. Create User and Past Epochs
            for item in data['origin_story']['past_authoring']:
                session.run("""
                    MERGE (h:Hero {name: $user})
                    MERGE (e:Epoch {title: $epoch})
                    SET e.experience = $experience
                    MERGE (h)-[:LIVED_THROUGH]->(e)
                """, user=data.get('user', os.environ.get("HERO_NAME", "Hero")), epoch=item['epoch'], experience=item['experience'])

            # 2. Map Future Ambitions as Quests/Goals
            for ambition in data['origin_story']['future_authoring']['ambitions']:
                session.run("""
                    MATCH (h:Hero {name: $user})
                    MERGE (q:Quest {title: $ambition})
                    SET q.status = 'active'
                    MERGE (h)-[:PURSUING]->(q)
                """, user=data.get('user', os.environ.get("HERO_NAME", "Hero")), ambition=ambition)
        
        logger.info("✅ Identity Graph synchronized successfully.")

    def analyze_alignment(self, activity_title):
        """
        Agentic Logic: Checks if a daily activity aligns with a Future Ambition.
        This is how we calculate the 'Hero's Rank' eventually.
        """
        story = self.load_origin_story()
        ambitions = story['origin_story']['future_authoring']['ambitions']
        
        prompt = f"""
        Given the user's Future Ambitions: {ambitions}
        Does the activity '{activity_title}' align with any of these?
        Answer with ONLY the name of the ambition or 'None'.
        """
        response = self.llm.invoke(prompt)
        return response.content.strip()

if __name__ == "__main__":
    brain = GTKYBrain()
    brain.sync_identity_to_graph()
    print("--- Porter Identity Sync Complete ---")