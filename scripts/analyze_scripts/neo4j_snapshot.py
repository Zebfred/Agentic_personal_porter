from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import json
from datetime import datetime
from neo4j import GraphDatabase

# Attempt to load path utils if script is run directly

from src.config import NeoConfig
from src.utils.path_utils import load_env_vars

class Neo4jSnapshotHandler:
    """
    Handles automated backups of the Neo4j Graph.
    Connects, fetches all Nodes and Relationships, and dumps to JSON.
    """
    def __init__(self):
        load_env_vars()
        self.driver = GraphDatabase.driver(
            NeoConfig.NEO4J_URI,
            auth=(NeoConfig.NEO4J_USER, NeoConfig.NEO4J_PASS)
        )
        self.backup_dir = root / "backups" / "neo4j_snapshots"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def close(self):
        self.driver.close()

    def create_snapshot(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.backup_dir / f"neo4j_snapshot_{timestamp}.json"
        
        logger.info(f"Creating Neo4j Snapshot: {filename}")
        
        # We query all nodes and relationships directly
        # For huge graphs, APOC export is better, but this works well for standard sizes
        nodes_query = "MATCH (n) RETURN id(n) AS id, labels(n) AS labels, properties(n) AS properties"
        rels_query = "MATCH (a)-[r]->(b) RETURN id(r) AS id, type(r) AS type, properties(r) AS properties, id(a) AS start_node, id(b) AS end_node"
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "nodes": [],
            "relationships": []
        }

        try:
            with self.driver.session() as session:
                logger.info("Fetching Nodes...")
                nodes_result = session.run(nodes_query)
                for record in nodes_result:
                    snapshot["nodes"].append({
                        "id": record["id"],
                        "labels": record["labels"],
                        "properties": record["properties"]
                    })
                
                logger.info("Fetching Relationships...")
                rels_result = session.run(rels_query)
                for record in rels_result:
                    snapshot["relationships"].append({
                        "id": record["id"],
                        "type": record["type"],
                        "start_node": record["start_node"],
                        "end_node": record["end_node"],
                        "properties": record["properties"]
                    })
            
            with open(filename, 'w') as f:
                json.dump(snapshot, f, indent=2, default=str)
                
            logger.info(f"✅ Snapshot successful. Exported {len(snapshot['nodes'])} nodes and {len(snapshot['relationships'])} relationships.")
            return str(filename)
            
        except Exception as e:
            logger.info(f"❌ Snapshot failed: {e}")
            return None

if __name__ == "__main__":
    handler = Neo4jSnapshotHandler()
    try:
        handler.create_snapshot()
    finally:
        handler.close()
