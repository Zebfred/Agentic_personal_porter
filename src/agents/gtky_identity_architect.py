import logging

logger = logging.getLogger(__name__)
import json
from pathlib import Path

from src.database.mongo_storage import SovereignMongoStorage
from src.utils.path_utils import get_project_root

root = get_project_root()


class GTKYIdentityArchitect:
    """
    The Identity Architect handles reading, scanning, and improving the
    fundamental user JSON artifacts: Origin Story, Ambitions, and Detriments.
    """

    def __init__(self, username: str = "system"):
        self.username = username
        self.artifacts_dir = root / "data" / "hero_artifacts"
        self.origin_file = self.artifacts_dir / "hero_origin.json"
        self.ambition_file = self.artifacts_dir / "hero_ambition.json"
        self.detriments_file = root / ".auth" / "hero_detriments.json"

    def _read_json(self, filepath: Path) -> dict:
        filename = filepath.name

        # 1. Mongo is Source of Truth
        try:
            mongo = SovereignMongoStorage()
            data = mongo.get_hero_artifact(filename, self.username)
            if data:
                return data
        except Exception as e:
            logger.info(f"Failed to reach Mongo for {filename}: {e}")

        # 2. Fallback to Local Filesystem
        if not filepath.exists():
            return {}
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                # Seed mongo if missing
                try:
                    SovereignMongoStorage().save_hero_artifact(filename, data, self.username)
                except Exception as e:
                    logger.warning(f"Non-critical error during identity processing: {e}")
                return data
        except Exception as e:
            logger.info(f"Error parsing {filepath}: {e}")
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

        data["pending_porter_updates"].append(
            {"timestamp": "Latest Porter Sync", "raw_update": raw_update_summary}
        )

        try:
            mongo = SovereignMongoStorage()
            mongo.save_hero_artifact(active_name, data, self.username)
            return f"Successfully routed the update to {active_name} inside MongoDB."
        except Exception as e:
            return f"Failed to persist to MongoDB: {e}"

    def get_origin_story(self):
        return self._read_json(self.origin_file)

    def get_ambition(self):
        return self._read_json(self.ambition_file)

    def get_detriments(self):
        return self._read_json(self.detriments_file)

    def scan_missing_artifacts(self):
        """
        Scans both `hero_origin.json` and `hero_ambition.json` for empty or placeholder
        fields and returns a structured `ArtifactGapReport` with interview prompts.
        """
        from src.schemas.hub_models import ArtifactGapItem, ArtifactGapReport

        gaps: list[ArtifactGapItem] = []

        origin_data = self.get_origin_story()
        if not origin_data or "origin_story" not in origin_data:
            gaps.append(
                ArtifactGapItem(
                    artifact_name="hero_origin.json",
                    field_path="origin_story.epochs",
                    prompt="Your Origin Story timeline has not been initialized yet. Which life epoch should we map first?",
                )
            )
        else:
            epochs = origin_data.get("origin_story", {}).get("epochs", [])
            for idx, ep in enumerate(epochs):
                name = ep.get("name", f"Epoch {idx + 1}")
                experiences = ep.get("experiences", [])
                if not experiences or "Proper Instructions coming soon" in name:
                    gaps.append(
                        ArtifactGapItem(
                            artifact_name="hero_origin.json",
                            field_path=f"origin_story.epochs[{idx}]",
                            prompt=f"Empty or placeholder epoch '{name}' in your Origin Story. What defining experiences belong here?",
                        )
                    )
                for exp_idx, exp in enumerate(experiences):
                    if not exp.get("title") and not exp.get("description"):
                        gaps.append(
                            ArtifactGapItem(
                                artifact_name="hero_origin.json",
                                field_path=f"origin_story.epochs[{idx}].experiences[{exp_idx}]",
                                prompt=f"Empty slot in epoch '{name}'. Candidate focus: {ep.get('experience candidate', [])}",
                            )
                        )
                    elif exp.get("title") and not str(exp.get("description", "")).strip():
                        gaps.append(
                            ArtifactGapItem(
                                artifact_name="hero_origin.json",
                                field_path=f"origin_story.epochs[{idx}].experiences[{exp_idx}].description",
                                prompt=f"Details needed for event '{exp.get('title')}' in '{name}'.",
                            )
                        )

        ambition_data = self.get_ambition()
        if not ambition_data or (
            isinstance(ambition_data, dict)
            and not ambition_data.get("data")
            and "Proper Instructions coming soon" in str(ambition_data.get("message", ""))
        ):
            gaps.append(
                ArtifactGapItem(
                    artifact_name="hero_ambition.json",
                    field_path="ambition.primary_quest",
                    prompt="Your Hero Ambition artifact has empty quests/milestones. What is your top 90-day Quest?",
                )
            )
        elif isinstance(ambition_data, dict):
            for key, val in ambition_data.items():
                if key == "pending_porter_updates":
                    continue
                if val in ("", [], {}, None):
                    gaps.append(
                        ArtifactGapItem(
                            artifact_name="hero_ambition.json",
                            field_path=f"ambition.{key}",
                            prompt=f"Ambition field '{key}' is currently empty. How would you define this goal?",
                        )
                    )
                elif isinstance(val, dict) and not str(val.get("description", "ok")).strip():
                    gaps.append(
                        ArtifactGapItem(
                            artifact_name="hero_ambition.json",
                            field_path=f"ambition.{key}.description",
                            prompt=f"Ambition '{key}' is missing a description or milestone target.",
                        )
                    )

        if not gaps:
            return ArtifactGapReport(
                status="success",
                has_gaps=False,
                gaps=[],
                results="Origin story and Hero Ambition artifacts are currently fully mapped out.",
            )

        bullet_lines = [f"- [{g.artifact_name}] {g.prompt}" for g in gaps[:4]]
        results_text = (
            "I noticed some gaps in your Hero Identity artifacts that need filling. Can you tell me more about:\n"
            + "\n".join(bullet_lines)
        )
        return ArtifactGapReport(
            status="success",
            has_gaps=True,
            gaps=gaps,
            results=results_text,
        )

    def scan_for_missing_origin(self) -> str:
        """
        Backwards-compatible string summary wrapper around `scan_missing_artifacts()`.
        """
        return self.scan_missing_artifacts().results
