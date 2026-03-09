import json
from datetime import datetime, timedelta
from neo4j import GraphDatabase
import os

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
        try:
            with self.driver.session() as session:
                return session.execute_read(self._fetch_context, user_name)
        except Exception as e:
            return {"error": str(e), "principles": [], "intentions": []}

    @staticmethod
    def _fetch_context(tx, name):
        # Query updated to handle standard 'Hero' naming conventions in Neo4j
        query = """
        MATCH (u:User) WHERE u.name CONTAINS $name
        OPTIONAL MATCH (u)-[:GUIDED_BY]->(p:Principle)
        OPTIONAL MATCH (u)-[:PURSUES]->(i:Intention)
        WHERE i.status = 'active' OR i.status IS NULL
        RETURN 
            collect(distinct p.text)[..3] as principles,
            collect(distinct i.title)[..5] as active_intentions
        """
        result = tx.run(query, name=name)
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

def run_15min_sanity_test():
    """
    Paul5 Quick Test: Verifies logic without needing live GCal/Neo4j if offline.
    """
    print("--- Starting Paul5 Sovereign Sanity Test ---")
    
    # Mock context mimicking hero_ambition.json
    mock_context = {
        "Principles": [
        "Aim for the highest possible good that is pleasing in the eyes of the lord.", 
        "--“Remembering that doing what you are capable of is respectable.”",
        "Pursue the Betterment of my craft, being open to the many forms of opportunity that can take.",
        "Teach and help others. Seek out being one that others can rely on.",
        "Build useful things. Do your best to have fun with it! And as often as possible, too!",
        "Make decisions to grant you more peace instead of what causes you more headaches"
        ],
        "Intent": [        
            {"Career Goal": "Grand RL Practioner of Model and Model-free based Modeling.Principal RL System architect.High Advance Profiency of modern LLM systems and implimentation expert. Competent Principle customer engineer & system admin.Advance practioner of Computer vision Modeling.Would like to be able to diagram tech systems as an Architect and project manager, so formal system design tools and advance competency of more non-techical diagramming and planning tools such as figma.Competent with Traditional and New Database structures and implimentation techinuques. Competent in Web navigation - html, css, js , php. To the degree that I can have useful conversations with other professionals or in support of other goals.Understanding of programming languages and the hardware that supports these systems and goals stated above."}, 
            {"Health Goal" : "Maintain eating habits that are good for mind and body in the long term. Getting adequate amount of sleep. Workout at least twice a week. Do stuff good for cardio"},
            {"Loved ones" : [
                {"Romantic Relationship Goal" : "Be emotionally available for my girlfriend. Do the necessary actions to bring us closer - create a greater depth in our relationship and bring us together in person."},
                {"Family Goal" : "Be reasonably available for my family."},
                {"Pet's Goal" : "Be a good dog dad. Take care of my dogs and give them a good life. Take them on fun adventures and give them lots of love and attention."}
            ]},
            {"Leisure Goal" : "Engage in social hobby activities.Engage in social hobby activities such as board games and caving opportunities. Enjoy quite hikes with dogs offleash"},
            {"Interest Goal" : "Explore interests of the world and reality that is not directly related to your career. Learning Hindi."},
            {"Spiritual Goal" : "Continue to read spiritual literature, meditate, pray, and leave space open to look to a higher power more than one’s own limited self-ego."},
            {"Social Goal":["To be a good person, and to be a good son, brother, friend, and partner. To be someone that others can rely on and trust. To be someone that is kind and helpful to others. To be someone that is fun to be around. To be someone that is always trying to improve themselves and their craft. To be someone that is always trying to do the right thing, even when it's hard.","Be available to friends, family, and people in my fellowship. Be polite and kind to strangers and be amiable when possible."]
            },
            {"Mundane Goal" : "Do the necessary things to maintain a comfortable and functional living space. Do the necessary things to maintain a comfortable and functional car. Do the necessary things to maintain a comfortable and functional wardrobe."},
            {"Detriments to Avoid" : "Avoid doing things that cause unnecessary stress and headaches. Avoid doing things that cause unnecessary conflict with others. Avoid doing things that cause unnecessary harm."} 
        ]
    }
    
    # Mock events
    mock_actual = [
        {"title": "Deep RL Study", "category": "Career Goal", "start": "2026-03-06T20:00", "duration_minutes": 60},
        {"title": "Scrolling Doom", "category": "Unknown", "start": "2026-03-06T21:00", "duration_minutes": 45}
    ]
    
    engine = SovereignContextEngine("bolt://localhost:7687", "neo4j", "password")
    
    print("Testing Delta Logic...")
    report = engine.analyze_day_delta([], mock_actual, mock_context)
    
    for entry in report:
        print(f"Result: [{entry['event']}] -> {entry['status']}")
    
    print("--- Test Complete ---")

if __name__ == "__main__":
    # If running directly, run the test
    run_15min_sanity_test()