import os
import sys
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.utils.path_utils import load_env_vars
from src.database.mongo_storage import SovereignMongoStorage

class GTKYIdentityArchitect:
    """
    The Identity Architect handles reading, scanning, and improving the
    fundamental user JSON artifacts: Origin Story, Ambitions, and Detriments.
    """
    def __init__(self):
        self.artifacts_dir = root / "data" / "hero_artifacts"
        self.origin_file = self.artifacts_dir / "hero_origin.json"
        self.ambition_file = self.artifacts_dir / "hero_ambition.json"
        self.detriments_file = root / ".auth" / "hero_detriments.json"
        
    def _read_json(self, filepath: Path) -> dict:
        filename = filepath.name
        
        # 1. Mongo is Source of Truth
        try:
            mongo = SovereignMongoStorage()
            data = mongo.get_hero_artifact(filename)
            if data:
                return data
        except Exception as e:
            print(f"Failed to reach Mongo for {filename}: {e}")

        # 2. Fallback to Local Filesystem
        if not filepath.exists():
            return {}
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                # Seed mongo if missing
                try:
                    SovereignMongoStorage().save_hero_artifact(filename, data)
                except: pass
                return data
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return {}
            
    def append_new_learnings(self, artifact_name: str, raw_update_summary: str) -> str:
        """
        Takes raw textual learnings from the Porter and attempts to logically inject them
        into the relevant Mongo artifact. (A more robust LLM agent should do the JSON syntax mapping later).
        For now, this serves as the persistent database route for the Porter.
        """
        # Right now we will append a "pending_porter_updates" field to the Mongo data
        data = None
        if "origin" in artifact_name:
             data = self.get_origin_story()
             active_name = "hero_origin.json"
        elif "ambition" in artifact_name:
             data = self.get_ambition()
             active_name = "hero_ambition.json"
        else:
             return "I do not recognize that artifact."
             
        if not data:
             return "Data model is empty, cannot append."
             
        if "pending_porter_updates" not in data:
             data["pending_porter_updates"] = []
             
        data["pending_porter_updates"].append({
             "timestamp": "Latest Porter Sync",
             "raw_update": raw_update_summary
        })
        
        try:
             mongo = SovereignMongoStorage()
             mongo.save_hero_artifact(active_name, data)
             return f"Successfully routed the update to {active_name} inside MongoDB."
        except Exception as e:
             return f"Failed to persist to MongoDB: {e}"

    def get_origin_story(self): return self._read_json(self.origin_file)
    def get_ambition(self): return self._read_json(self.ambition_file)
    def get_detriments(self): return self._read_json(self.detriments_file)

    def scan_for_missing_origin(self) -> str:
        """
        Scans hero_origin.json for epochs with missing or sparse descriptions.
        If gaps are found, it generates interview targets to feed back to the user via the frontend.
        """
        data = self.get_origin_story()
        if not data or "origin_story" not in data:
             return "No origin story base found to scan."
             
        missing_prompts = []
        epochs = data.get("origin_story", {}).get("epochs", [])
        for ep in epochs:
            name = ep.get('name', 'Unknown Epoch')
            for exp in ep.get('experiences', []):
                 if not exp.get('title') and not exp.get('description'):
                      missing_prompts.append(f"- Empty slot in epoch: '{name}'. Candidate focus: {ep.get('experience candidate', [])}")
                 elif exp.get('title') and (not exp.get('description') or exp.get('description') == ""):
                      missing_prompts.append(f"- Details needed for event: '{exp.get('title')}' in '{name}'.")
                      
        if not missing_prompts:
             return "Origin story is currently fully mapped out."
             
        out = "I noticed some gaps in your Origin Story timeline that need filling. Can you tell me more about:\n"
        out += "\n".join(missing_prompts[:3]) # Only ask about 3 at a time to reduce cognitive load
        return out
