import sys
import os
import json

# Ensure we can import from the src directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define our paths exactly as they are in the project
ARTIFACTS_DIR = os.path.join(os.getcwd(), 'data', 'hero_artifacts')
AMBITION_PATH = os.path.join(ARTIFACTS_DIR, 'hero_ambition.json')
ORIGIN_PATH = os.path.join(ARTIFACTS_DIR, 'hero_origin.json') 

def flatten_intents(raw_intents):
    flattened = []
    for intent_dict in raw_intents:
        for main_category, value in intent_dict.items():
            if isinstance(value, str):
                flattened.append({"category": main_category, "description": value, "parent_category": "None"})
            elif isinstance(value, list):
                if all(isinstance(i, str) for i in value):
                    flattened.append({"category": main_category, "description": " ".join(value), "parent_category": "None"})
                elif all(isinstance(i, dict) for i in value):
                    # Emit the parent node first!
                    flattened.append({"category": main_category, "description": "Sub-goals contained within.", "parent_category": "None"})
                    # Then emit the children linked to the parent
                    for sub_dict in value:
                        for sub_cat, sub_desc in sub_dict.items():
                            flattened.append({"category": sub_cat, "description": sub_desc, "parent_category": main_category})
    return flattened

def process_epochs(raw_epochs):
    processed_epochs = []
    processed_experiences = []

    for epoch in raw_epochs:
        epoch_name = epoch.get("name", "Unknown Epoch")
        timeframe = epoch.get("timeframe", "Unknown Timeframe")
        
        processed_epochs.append({"name": epoch_name, "timeframe": timeframe})

        for exp in epoch.get("experiences", []):
            title = exp.get("title", "").strip()
            desc = exp.get("description", "").strip()
            status = "Logged" if desc else "Needs_Detail"
            if title or desc:
                processed_experiences.append({
                    "epoch_name": epoch_name, 
                    "title": title if title else "Untitled Memory", 
                    "description": desc, 
                    "status": status
                })

        for candidate in epoch.get("experience candidate", []):
            if isinstance(candidate, str) and candidate.strip():
                processed_experiences.append({
                    "epoch_name": epoch_name, 
                    "title": candidate.strip(),
                    "description": "", 
                    "status": "Candidate"
                })

    return processed_epochs, processed_experiences

def dry_run_parsing():
    print("✨ Starting Dry-Run Parsing Audit ✨\n")

    # 1. Audit Ambitions
    if os.path.exists(AMBITION_PATH):
        with open(AMBITION_PATH, 'r') as file:
            ambition_data = json.load(file)
        principles = ambition_data.get("Principles", [])
        flat_intents = flatten_intents(ambition_data.get("Intent", []))
        
        print(f"🌟 PRINCIPLES PARSED: {len(principles)}")
        print(f"🌟 INTENTS PARSED: {len(flat_intents)}")
        print("-" * 40)
    else:
        print(f"❌ Missing {AMBITION_PATH}")

    # 2. Audit Origins & Draw the Hierarchy Tree
    if os.path.exists(ORIGIN_PATH):
        with open(ORIGIN_PATH, 'r') as file:
            origin_data = json.load(file)
        raw_epochs = origin_data.get("origin_story", {}).get("epochs", [])
        epochs_data, experiences_data = process_epochs(raw_epochs)
        
        print(f"⏳ EPOCHS PARSED: {len(epochs_data)}")
        print(f"🧠 EXPERIENCES PARSED: {len(experiences_data)}")
        print("\n🌳 GRAPH HIERARCHY AUDIT (Origin -> Epoch -> Experiences):")
        print("(Hero) Zeb")
        print("  └── (Origin) Zeb's Story")
        
        # Loop through the parsed epochs to prove the linkage!
        for epoch in epochs_data:
            print(f"       └── (Epoch) {epoch['name']} [{epoch['timeframe']}]")
            
            # Find all experiences that belong to this specific epoch
            epoch_exps = [exp for exp in experiences_data if exp['epoch_name'] == epoch['name']]
            
            for exp in epoch_exps:
                # Add a cute little icon based on the status so you can see what the Mach 3 agent will target
                status_icon = "📝" if exp['status'] == "Logged" else "✨"
                print(f"            └── (Experience) {exp['title']} [{status_icon} {exp['status']}]")
    else:
        print(f"❌ Missing {ORIGIN_PATH}")

    print("\n✅ Dry-Run Complete! Your data is looking lovely and ready for injection.")

if __name__ == "__main__":
    dry_run_parsing()