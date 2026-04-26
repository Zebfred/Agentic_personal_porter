import os
import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).resolve().parent.parent
sys.path.append(str(root))

from src.database.neo4j_client import get_driver

def wipe_graph():
    """
    WARNING: Wipes the entire Neo4j graph. Use with extreme caution.
    This is intended to clear the legacy single-user graph before starting the new multi-user architecture.
    """
    print("WARNING: You are about to delete ALL nodes and relationships in the Neo4j database.")
    confirmation = input("Type 'WIPE' to confirm: ")
    
    if confirmation != "WIPE":
        print("Operation cancelled.")
        return

    driver = get_driver()
    if not driver:
        print("Could not connect to Neo4j. Check credentials in .env")
        return

    try:
        with driver.session() as session:
            # Neo4j recommends executing large deletes in batches if the graph is huge,
            # but for a personal graph, a simple DETACH DELETE usually works fine.
            print("Wiping graph...")
            result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted_count")
            summary = result.single()
            deleted = summary["deleted_count"] if summary else 0
            
            print(f"Graph wipe successful. Deleted {deleted} nodes.")
    except Exception as e:
        print(f"Error wiping graph: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    wipe_graph()
