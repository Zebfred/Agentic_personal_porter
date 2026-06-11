from dotenv import load_dotenv

load_dotenv()

from src.database.neo4j_client.connection import get_driver

class SovereignContextEngine:
    """
    The 'Bridge' between the Neo4j Identity Graph and the CrewAI Agents.
    Extracts high-fidelity context snapshots to ground the LLM.
    """
    def __init__(self):
        self.driver = get_driver()

    def close(self):
        """No-op as connection is managed by singleton."""
        pass

    def get_hero_snapshot(self, username="Hero"):
        """
        Fetches the active 'Hero' context to feed into the Agent System Prompt.
        """
        try:
            with self.driver.session() as session:
                return session.execute_read(self._fetch_context, username)
        except Exception as e:
            return {"error": str(e), "principles": [], "intentions": []}

    @staticmethod
    def _fetch_context(tx, username):
        # Using the canonical schema defined in inject_hero_foundation.py:
        # (h:Hero)-[:DIRECTED_BY]->(art:Artifacts)
        query = """
        MATCH (h:Hero)-[:DIRECTED_BY]->(art:Artifacts)
        WHERE h.hero CONTAINS $username
        OPTIONAL MATCH (art)-[:GUIDED_BY]->(p:Principle)
        OPTIONAL MATCH (art)-[:HAS_INTENT]->(i:Intent)
        RETURN 
            collect(distinct p.text) as principles,
            collect(distinct i.category)[..5] as active_intentions
        """
        result = tx.run(query, username=username)
        record = result.single()
        if not record:
            return {"principles": [], "intentions": []}
        return {
            "principles": record["principles"],
            "intentions": record["active_intentions"]
        }

    def analyze_day_delta(self, planned_events, actual_events, hero_context):
        """
        $\Delta = Intent - Actual$
        """
        delta_report = []
        for actual in actual_events:
            match = next((p for p in planned_events if p.get('start') == actual.get('start')), None)
            delta_status = self.calculate_delta(match, actual, hero_context)
            delta_report.append({
                "event": actual.get('title', 'Unnamed'),
                "status": delta_status,
                "timestamp": actual.get('start')
            })
        return delta_report

    def calculate_delta(self, planned, actual, context):
        """
        Logic for categorizing the gap between Intent and Reality.
        Refined for hero_ambition category matching.
        """
        category = actual.get('category', 'Unknown')
        
        # 1. Fog of War Check
        if category == 'Unknown' or not category:
            duration = actual.get('duration_minutes', 0)
            return "Fog of War" if duration > 30 else "Unaccounted"

        # 2. Alignment Check
        # Does the actual category exist in our Neo4j 'Active Intentions'?
        intentions = [i.lower() for i in context.get('intentions', [])]
        is_aligned = any(category.lower() in intent for intent in intentions)

        if not planned:
            return "Valuable Detour" if is_aligned else "Spontaneous Action"

        if planned.get('category') == category:
            return "Forward Progress"
        
        return "High-Friction Deviation"
