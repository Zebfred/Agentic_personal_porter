import os
import sys
from neo4j import GraphDatabase

# Configure python path to find src if running locally
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import NeoConfig

def wipe_graph():
    print("Initiating full Neo4j Graph wipe for clean Mach 2 format...")
    driver = GraphDatabase.driver(NeoConfig.NEO4J_URI, auth=(NeoConfig.NEO4J_USER, NeoConfig.NEO4J_PASS))
    
    with driver.session() as session:
        result = session.run("MATCH (n) DETACH DELETE n")
        summary = result.consume()
        nodes_deleted = summary.counters.nodes_deleted
        rels_deleted = summary.counters.relationships_deleted
        
    print(f"Purge Complete! Deleted {nodes_deleted} nodes and {rels_deleted} relationships.")
    driver.close()

if __name__ == "__main__":
    wipe_graph()
