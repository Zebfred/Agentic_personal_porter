import os
from datetime import datetime, timedelta
from src.database.context_engine import SovereignContextEngine
from src.database.mongo_storage import SovereignMongoStorage

class SocraticMirrorEngine:
    """
    The 'Logic' behind the Socratic Mirror.
    Calculates the Delta between what Zeb intended (Neo4j) 
    and what Zeb actually did (MongoDB/GCal).
    """
    def __init__(self):
        self.context = SovereignContextEngine()
        self.storage = SovereignMongoStorage()

    def calculate_daily_delta(self, days_back=1):
        """
        Performs the Mach 2 Delta Calculation: Delta = Intent - Actual.
        """
        # 1. Get Hero DNA (Principles/Active Intentions)
        hero_dna = self.context.get_hero_snapshot(user_name="Zeb")
        
        # 2. Get Formatted Events from the last 24 hours
        # In a demo, we might pull a specific 'high-friction' day
        recent_events = self.storage.formatted_col.find({
            "record_type": "Actual"
        }).sort("start", -1).limit(5)

        analysis = {
            "hero_principles": hero_dna['principles'],
            "active_intentions": hero_dna['intentions'],
            "observations": []
        }

        for event in recent_events:
            # Logic: If an Actual Pillar doesn't match an Active Intention, it's a 'Detour'
            pillar = event.get('pillar')
            is_intentional = any(pillar.lower() in intent.lower() for intent in hero_dna['intentions'])
            
            status = "Aligned" if is_intentional else "Valuable Detour"
            if pillar == "Uncategorized":
                status = "Fog of War"

            analysis["observations"].append({
                "title": event.get('title'),
                "pillar": pillar,
                "status": status,
                "duration": event.get('duration_minutes')
            })

        return analysis

    def generate_socratic_prompt(self, analysis):
        """
        Converts raw data into a Socratic Prompt for the CrewAI Agent.
        """
        observations_str = "\n".join([
            f"- {obs['title']} ({obs['duration']}m): {obs['status']} [{obs['pillar']}]"
            for obs in analysis['observations']
        ])
        
        prompt = f"""
        SIR'S RECENT DATA:
        {observations_str}

        CORE PRINCIPLES: {analysis['hero_principles']}
        
        TASK:
        As the Socratic Mirror, identify the most significant 'Valuable Detour'. 
        Instead of judging, ask ONE question that helps Zeb understand if his 
        Current Epoch (Action) is drifting from his Sovereign Intent (Graph).
        """
        return prompt