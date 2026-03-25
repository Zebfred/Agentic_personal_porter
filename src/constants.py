import os
from pathlib import Path

# Find root
root_dir = Path(__file__).resolve().parent.parent
import json

# --- THE LIFE PILLAR MAP ---
# This is the "Learning" base. We map keywords and Google Colors to Pillars.
mapping_file_path = root_dir / ".auth" / "category_mapping.json"
example_file_path = root_dir / "data" / "category_mapping.example.json"

try:
    if mapping_file_path.exists():
        with open(mapping_file_path, 'r') as f:
            ACTUAL_CATEGORY_MAPPING = json.load(f)
    else:
        # Fallback to example mapping if the protected one doesn't exist
        with open(example_file_path, 'r') as f:
            ACTUAL_CATEGORY_MAPPING = json.load(f)
except Exception as e:
    print(f"Warning: Could not load category mapping. {e}")
    ACTUAL_CATEGORY_MAPPING = {"intent_to_actual_mapping": {}, "actual_categorization_with_keywords": {}, "colors": {}}