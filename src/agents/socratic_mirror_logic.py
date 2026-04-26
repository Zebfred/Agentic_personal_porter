import os
from datetime import datetime, timedelta
from src.database.context_engine import SovereignContextEngine
from src.database.mongo_storage import SovereignMongoStorage

class SocraticMirrorEngine:
    """
    The 'Logic' behind the Socratic Mirror.
    Calculates the Delta between what the hero intended (Neo4j) 
    and what they actually did (MongoDB/GCal).
    """
    def __init__(self):
        self.context = SovereignContextEngine()
        self.storage = SovereignMongoStorage()

    def calculate_daily_delta(self, days_back=1):
        """
        Performs the Mach 2 Delta Calculation: Delta = Intent - Actual.
        Also detects "Fog of War" gaps between recorded events.
        """
        from src.database.mongo_client.agent_health import AgentHeartbeatManager
        health_manager = AgentHeartbeatManager()
        run_id = health_manager.start_agent_run("socratic_mirror_logic", {"action": "calculate_daily_delta", "days_back": days_back})
        
        try:
            # 1. Get Hero DNA (Principles/Active Intentions)
            hero_name = os.environ.get("HERO_NAME", "Hero")
            hero_dna = self.context.get_hero_snapshot(user_name=hero_name)
            
            # 2. Get Formatted Events from the last 24 hours
            cutoff = datetime.now() - timedelta(days=days_back)
            recent_events = list(self.storage.formatted_col.find({
                "record_type": "Actual",
                # We assume ISO strings or dates can be sorted/filtered
            }).sort("start", 1)) # Sort ascending to calculate gaps
            
            # In a real scenario we filter by date, but since Mongo query is basic here,
            # we'll just process the last 15 events ascending if we want a sample
            if len(recent_events) > 15:
                recent_events = recent_events[-15:]

            analysis = {
                "hero_principles": hero_dna['principles'],
                "active_intentions": hero_dna['intentions'],
                "observations": []
            }

            previous_end_time = None

            for event in recent_events:
                # Parse start and duration
                start_str = event.get('start')
                duration = event.get('duration_minutes', 0)
                
                # Basic parsing (assumes ISO8601 string from parser)
                try:
                    # remove timezone info for simple gap math if needed, or use fromisoformat
                    start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    
                    # Check for Fog of War gap
                    if previous_end_time:
                        gap = (start_time - previous_end_time).total_seconds() / 60.0
                        if gap > 60: # Gap larger than 1 hour
                            analysis["observations"].append({
                                "title": "Untracked Time",
                                "pillar": "Uncategorized",
                                "status": "Fog of War",
                                "duration": int(gap)
                            })
                    
                    previous_end_time = start_time + timedelta(minutes=duration)
                except Exception:
                    pass # Skip gap logic if parsing fails

                pillar = event.get('pillar', 'Uncategorized')
                is_intentional = any(pillar.lower() in intent.lower() for intent in hero_dna['intentions'])
                
                status = "Aligned" if is_intentional else "Valuable Detour"
                if pillar == "Uncategorized":
                    status = "Fog of War"

                analysis["observations"].append({
                    "title": event.get('title', 'Unknown Event'),
                    "pillar": pillar,
                    "status": status,
                    "duration": duration
                })

            health_manager.end_agent_run(run_id, status="success", result_summary=f"Processed {len(recent_events)} events.")
            return analysis
        except Exception as e:
            health_manager.end_agent_run(run_id, status="fail", error_msg=str(e))
            raise e

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
        As the Socratic Mirror, review the recent observations. Pay special attention to 'Fog of War' entries, 
        which represent untracked gaps in time or completely uncategorized activities.
        
        Instead of judging, ask ONE potent question that forces the hero to reflect:
        Was the recent untracked 'Fog of War' period a conscious act of 'Restorative Rest' 
        that aligns with their principles, or was it a slide into 'Mindless Stagnation'?
        Keep the question brief, piercing, and Socratic.
        """
        return prompt