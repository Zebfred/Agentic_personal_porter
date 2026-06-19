import json
import logging
import re
from typing import List, Dict, Any
from src.utils.llm_factory import AgentLLMConfig
from langchain_core.prompts import ChatPromptTemplate
from src.utils.path_utils import load_env_vars

logger = logging.getLogger(__name__)

class GTKYBaseClassifier:
    """
    Base class for GTKY agents that classify calendar events into Golden Objects.
    """
    def __init__(self):
        load_env_vars()
        from src.database.mongo_storage import SovereignMongoStorage
        self.storage = SovereignMongoStorage()

    def _load_artifact(self, artifact_name: str, username: str = "system") -> Dict[str, Any]:
        """Loads artifact from MongoDB."""
        data = self.storage.get_hero_artifact(artifact_name, username)
        if not data:
            logger.error(f"❌ Artifact missing in DB: {artifact_name} for {username}")
            return {}
        return data

    def _classify_batch(self, events: List[Dict], username: str, agent_role: str, time_context: str, log_emoji: str) -> List[Dict]:
        """
        Processes a batch of raw events, bundles them with Hero Context,
        and uses LLM classification to mint "Golden Objects".
        Processes in chunks of 10 to avoid token and json formatting issues.
        """
        # Load Contexts
        origin_ctx = self._load_artifact("hero_origin", username)
        ambition_ctx = self._load_artifact("hero_ambition", username)
        mapping_ctx = self._load_artifact("category_mapping", username)
        
        # System Prompt
        system_prompt = f"""You are the GTKY {agent_role} Agent. Your duty is to review {username}'s raw {time_context} Google Calendar events 
and rigidly classify them into "Golden Objects" based on {username}'s Origin Story and Ambitions.

Context of the Hero ({username}):
Origin: {{origin}}
Ambitions/Intent: {{ambition}}

Category Mapping Guidelines:
{{category_mapping}}

Given a list of JSON calendar events, analyze each and output exactly a valid JSON array of objects with the following identical schema.
If an event falls under a specific ambition (e.g., "Career Goal"), use that as the 'pillar'. If not, categorize it broadly (e.g., "Social", "Rest", "Maintenance").

Schema per object:
{{{{
  "gcal_id": "string (MUST MATCH the input gcal_id exactly)",
  "title": "string (MUST MATCH the input title exactly)",
  "start": "string (MUST MATCH the input start exactly)",
  "duration_minutes": int (MUST MATCH the input duration_minutes exactly),
  "record_type": "Actual",
  "pillar": "string (Must map to an ambition category or generic)",
  "subcategory": "string (More detailed description)",
  "is_valuable_detour": boolean (True if it was an unplanned but positive diversion)
}}}}

Output ONLY the raw JSON array. No markdown blocks, no chat formatting.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", f"Here is the {time_context} batch of calendar events:\n{{events_batch}}")
        ])
        
        # Primary: Groq Llama 3.3 70b (Bypasses Gemini API limits, highly capable of JSON reasoning)
        primary_config = AgentLLMConfig(provider="groq", model="llama-3.3-70b-versatile", temperature=0.0)
        primary_llm = primary_config.get_chat_model()
        
        # Fallback: Groq Llama 3.1 8b
        fallback_config = AgentLLMConfig(provider="groq", model="llama-3.1-8b-instant", temperature=0.0)
        fallback_llm = fallback_config.get_chat_model()
        llm_with_fallback = primary_llm.with_fallbacks([fallback_llm])
            
        chain = prompt | llm_with_fallback
        
        import time
        golden_objects = []
        chunk_size = 25  # Increased to reduce total API calls
        
        for i in range(0, len(events), chunk_size):
            chunk = events[i:i + chunk_size]
            events_subset = []
            for ev in chunk:
                gcal_id = ev.get("id") or ev.get("gcal_id")
                
                # Pre-parse start and end times
                start_obj = ev.get("start", {})
                end_obj = ev.get("end", {})
                start_iso = start_obj.get("dateTime") or start_obj.get("date")
                end_iso = end_obj.get("dateTime") or end_obj.get("date")
                
                duration_minutes = 0
                if start_iso and end_iso:
                    try:
                        from dateutil import parser
                        st = parser.parse(start_iso)
                        et = parser.parse(end_iso)
                        duration_minutes = int((et - st).total_seconds() / 60)
                    except Exception:
                        pass
                
                # Simplification: we forward 'start', 'duration_minutes', 'title', 'gcal_id'
                events_subset.append({
                    "gcal_id": gcal_id,
                    "title": ev.get("summary", "Untitled Event"),
                    "start": start_iso,
                    "duration_minutes": duration_minutes,
                    "description": ev.get("description", "")
                })
                
            logger.info(f"{log_emoji} {agent_role} processing {time_context} batch {i} to {i + len(chunk)}...")
            
            try:
                response = chain.invoke({
                    "origin": json.dumps(origin_ctx),
                    "ambition": json.dumps(ambition_ctx),
                    "category_mapping": json.dumps(mapping_ctx) if mapping_ctx else "{}",
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
                        if "gcal_id" in obj and obj["gcal_id"] is not None:
                            obj.setdefault("start", "")
                            obj.setdefault("duration_minutes", 0)
                            obj.setdefault("pillar", "Unclassified")
                            obj.setdefault("record_type", "Actual")
                            golden_objects.append(obj)
            except Exception as e:
                logger.error(f"❌ Failed to classify chunk {i}: {e}")
                
            # Vertex AI has generous rate limits; light delay to be polite
            time.sleep(0.5)
                
        return golden_objects
