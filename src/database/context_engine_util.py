import json
from datetime import datetime, timedelta
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
            "intentions": record["active_intentions"]
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

    def analyze_day_delta(self, planned_events, actual_events, hero_context):
        """
        Rough draft of the Delta Engine logic to process a list of events.
        $\Delta = Intent - Actual$
        """
        delta_report = []
        
        # Simple reconciliation loop
        for actual in actual_events:
            # Find matching planned event by time/category
            match = next((p for p in planned_events if p['start'] == actual['start']), None)
            
            delta_status = self.calculate_delta(match, actual, hero_context)
            delta_report.append({
                "event": actual['title'],
                "status": delta_status,
                "timestamp": actual['start']
            })
            
        return delta_report

    def calculate_delta(self, planned, actual, context):
        """
        Core logic for categorizing the gap between Intent and Reality.
        """
        # 1. Fog of War: Actual exists but is unlabeled or long and unknown
        if not actual.get('category') or actual.get('category') == 'Unknown':
            duration = actual.get('duration_minutes', 0)
            if duration > 30:
                return "Fog of War"
            return "Unaccounted"

        # 2. No Plan: If we didn't plan it, check if it's a 'Valuable Detour'
        if not planned:
            # Check if the actual category aligns with Core Principles or Intentions
            is_aligned = any(actual['category'].lower() in goal.lower() for goal in context['intentions'])
            if is_aligned:
                return "Valuable Detour"
            return "Spontaneous Action"

        # 3. Direct Comparison
        # Check for Forward Progress (Category match and within 15m variance)
        if planned['category'] == actual['category']:
            # For rough draft, assuming time match is handled by the loop
            return "Forward Progress"
        
        # 4. Friction: Category mismatch
        return "High-Friction Deviation"

# --- Example Usage Logic ---

def example_reconciliation():
    # Placeholder for the future implementation
    # actual_event = {"title": "Coded Porter", "category": "Career Goal", "start": "2024-03-07T20:00:00"}
    # planned_event = {"title": "Gym", "category": "Health Goal", "start": "2024-03-07T20:00:00"}
    pass