import json
from neo4j import GraphDatabase
# Note: Ensure path_utils.py is used to resolve the project root

class SovereignContextEngine:
    """
    The 'Bridge' between the Neo4j Identity Graph and the CrewAI Agents.
    Extracts high-fidelity context snapshots to ground the LLM.
    """
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_hero_snapshot(self, user_name="Sir"):
        """
        Fetches the active 'Hero' context to feed into the Agent System Prompt.
        """
        with self.driver.session() as session:
            return session.execute_read(self._fetch_context, user_name)

    @staticmethod
    def _fetch_context(tx, name):
        # Query to get the user's current goals and top principles
        query = """
        MATCH (u:User {name: $name})
        OPTIONAL MATCH (u)-[:GUIDED_BY]->(p:Principle)
        OPTIONAL MATCH (u)-[:PURSUES]->(i:Intention)
        WHERE i.status = 'active'
        RETURN 
            collect(distinct p.text)[..3] as principles,
            collect(distinct i.title)[..5] as active_intentions
        """
        result = tx.run(query, name=name)
        record = result.single()
        return {
            "principles": record["principles"],
            "intentions": record["intentions"]
        }

    def generate_agent_injection_json(self, context_dict):
        """
        Formats the context for CrewAI Task descriptions.
        """
        return json.dumps({
            "sovereign_context": {
                "active_intentions": context_dict["intentions"],
                "core_principles": context_dict["principles"],
                "instruction": "You must prioritize these intentions when analyzing current GCal noise."
            }
        }, indent=2)

# --- Delta Calculation Logic Helper ---

def calculate_delta(planned_start, actual_start, duration_variance):
    """
    Implements: Delta = Actual - Intent
    Returns a categorization for the Inventory Curator.
    """
    # Logic to be implemented tonight:
    # 1. Compare timestamps
    # 2. Check Pillar alignment
    # 3. Return 'Achieved', 'Detour', or 'Fog'
    pass