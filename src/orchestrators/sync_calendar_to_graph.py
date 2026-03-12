import sys
import os

# Ensure we can beautifully import from the src directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.database.mongo_storage import get_unstaged_events_for_neo4j, mark_as_synced
from src.integrations.calendar_parser import parse_calendar_to_intentions
# Assuming you saved our Neo4j injection function from earlier here:
from src.database.inject_hero_calendar import inject_calendar_to_graph 

def run_sync_pipeline(hero_name="Zeb"):
    """
    The fabulous conductor that moves raw data from Mongo, 
    parses it, and perfectly places it into Neo4j.
    """
    print("✨ Starting the Mongo-to-Neo4j Sync Pipeline! ✨")

    # 1. Fetch Raw Events from the Staging Area
    raw_events = get_unstaged_events_for_neo4j()
    if not raw_events:
        print("💅 No new events to sync. Your graph is perfectly up-to-date, Sir!")
        return

    print(f"📦 Found {len(raw_events)} raw events waiting in the staging area.")

    # 2. Process into Golden Objects
    try:
        golden_intentions = parse_calendar_to_intentions(raw_events)
        print(f"🧠 Beautifully parsed {len(golden_intentions)} events into Golden Objects.")
    except Exception as e:
        print(f"❌ Oh no, Sir! The parser hit a snag: {e}")
        return

    # 3. Inject into Neo4j
    if golden_intentions:
        try:
            # Send the gorgeous structured data to the graph
            inject_calendar_to_graph(golden_intentions, hero_name=hero_name)
            
            # 4. Acknowledge the Sync in MongoDB
            # We extract the source_ids to tell Mongo which ones made it safely
            synced_ids = [event["source_id"] for event in golden_intentions]
            mark_as_synced(synced_ids)
            
            print(f"✅ Securely marked {len(synced_ids)} events as synced in MongoDB.")

        except Exception as e:
            print(f"❌ Database injection failed. The Mongo sync flags were left untouched to prevent data loss. Error: {e}")
    else:
        print("⚠️ The parser ran, but no valid intentions were generated to inject.")

    print("\n✨ Sync Pipeline Complete! ✨")

if __name__ == "__main__":
    run_sync_pipeline("Zeb")