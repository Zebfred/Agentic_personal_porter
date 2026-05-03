import os
import json
import logging
import re
from typing import List, Dict, Any
from pydantic import BaseModel, SecretStr
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
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
        system_prompt = f"""You are the GTKY {agent_role} Agent. Your duty is to review the user's raw {time_context} Google Calendar events 
and rigidly classify them into "Golden Objects" based on the user's Origin Story and Ambitions.

Context of the Hero:
Origin: {{origin}}
Ambitions/Intent: {{ambition}}

Category Mapping Guidelines:
{{category_mapping}}

Given a list of JSON calendar events, analyze each and output exactly a valid JSON array of objects with the following identical schema.
If an event falls under a specific ambition (e.g., "Career Goal"), use that as the 'pillar'. If not, categorize it broadly (e.g., "Social", "Rest", "Maintenance").

Schema per object:
{{{{
  "gcal_id": "string (MUST MATCH the input gcal_id exactly)",
  "title": "string",
  "start": "string",
  "duration_minutes": int,
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
        
        groq_api_key = os.getenv("GROQ_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not groq_api_key:
            logger.error("No GROQ_API_KEY found in environment.")
            return []
            
        primary_llm = ChatGroq(
            api_key=SecretStr(groq_api_key),
            model="llama-3.3-70b-versatile",
            temperature=0.0
        )
        
        if openai_api_key:
            fallback_llm = ChatOpenAI(
                api_key=SecretStr(openai_api_key),
                model="gpt-5.4-mini",
                temperature=0.0
            )
            llm_with_fallback = primary_llm.with_fallbacks([fallback_llm])
        else:
            logger.warning("No OPENAI_API_KEY found, fallback disabled.")
            llm_with_fallback = primary_llm
            
        chain = prompt | llm_with_fallback
        
        golden_objects = []
        chunk_size = 10
        
        for i in range(0, len(events), chunk_size):
            chunk = events[i:i + chunk_size]
            events_subset = []
            for ev in chunk:
                # Simplification: we forward 'start', 'end', 'summary', 'gcal_id'
                events_subset.append({
                    "gcal_id": ev.get("gcal_id"),
                    "summary": ev.get("summary"),
                    "start": ev.get("start"),
                    "end": ev.get("end")
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
                        if "gcal_id" in obj:
                            golden_objects.append(obj)
            except Exception as e:
                logger.error(f"❌ Failed to classify chunk {i}: {e}")
                
        return golden_objects
