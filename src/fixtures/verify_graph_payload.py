from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import sys
import json
from collections import defaultdict

# Path resolution to ensure we can reach database and integration modules

from src.database.mongo_storage import SovereignMongoStorage
from src.utils.path_utils import get_project_root


def verify_local_graph_structure(hero_name: str):
    root = get_project_root()
    if not hero_name:
        raise ValueError("hero_name is required for graph verification")

    """
    Pulls formatted data from MongoDB and constructs a local representation 
    of the Neo4j Graph to verify relationships and classifications.
    """
    logger.info(f"--- 🔍 Simulating Identity Graph for: {hero_name} ---")

    storage = SovereignMongoStorage()

    # Phase 1: Fetch formatted events ready for the graph
    events = storage.get_formatted_for_neo4j()

    if not events:
        logger.info("⚠️ No formatted events found in MongoDB. Run mongo_storage.py first.")
        return

    # Phase 2: Construct the Local Hierarchy
    # Structure: Graph[Calendar][RecordType][Pillar] -> [Events]
    local_graph = {
        "Hero": hero_name,
        "Calendar": "Primary",
        "Structure": {
            "Intention": defaultdict(list), # Planned/Blueprint events
            "Actual": defaultdict(list)     # Realized/Logged events
        }
    }

    logger.info(f"Processing {len(events)} events into graph hierarchy...")

    for event in events:
        # Extract metadata for classification mapping
        record_type = event.get('record_type', 'Unknown')
        pillar = event.get('pillar', 'Uncategorized')
        subcategory = event.get('subcategory', 'General')

        # Build the leaf node
        event_node = {
            "title": event.get('title'),
            "start": event.get('start'),
            "duration": f"{event.get('duration_minutes')}m",
            "gcal_id": event.get('gcal_id'),
            "classification": {
                "intent_bridge": pillar,
                "goal_detail": subcategory
            }
        }

        # Place into hierarchy
        if record_type in local_graph["Structure"]:
            local_graph["Structure"][record_type][pillar].append(event_node)

    # Phase 3: Reporting & Verification
    logger.info("\n--- ✅ Graph Verification Report ---")

    for r_type, pillars in local_graph["Structure"].items():
        total_type = sum(len(evs) for evs in pillars.values())
        logger.info(f"\n[Record Type: {r_type}] - Total: {total_type}")

        for pillar, event_list in pillars.items():
            logger.info(f"  └── Intent: {pillar} ({len(event_list)} events)")
            # Show a sample of the first event in this pillar for verification
            if event_list:
                sample = event_list[0]
                logger.info(f"      📍 Sample: \"{sample['title']}\" -> [{sample['classification']['goal_detail']}]")

    # Optional: Save a snapshot for Vim review
    snapshot_path = root / "data" / "graph_structure_snapshot.json"
    with open(snapshot_path, 'w') as f:
        json.dump(local_graph, f, indent=4)

    logger.info(f"\nFull graph snapshot saved to: {snapshot_path}")
    logger.info("Use 'vi' to inspect the full mapping and verify Goal Classifications.")

if __name__ == "__main__":
    hero = sys.argv[1] if len(sys.argv) > 1 else "Hero"
    verify_local_graph_structure(hero)