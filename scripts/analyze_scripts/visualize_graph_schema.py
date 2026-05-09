import os
import sys
import json
from pathlib import Path

# Add project root to path
root = Path(__file__).resolve().parent.parent
sys.path.append(str(root))

from src.database.neo4j_client import get_driver

def visualize_schema():
    """
    Connects to Neo4j, queries the db.schema.visualization procedure,
    and prints a structured JSON of the node labels and relationship types currently active in the graph.
    """
    driver = get_driver()
    if not driver:
        print("Could not connect to Neo4j. Check credentials in .env")
        return

    try:
        with driver.session() as session:
            # Call the built-in Neo4j schema visualization procedure (Requires APOC usually, or built-in schema tools depending on version)
            # Alternative: use standard cypher to extract distinct labels and rels
            print("Extracting current Graph Schema...")
            
            nodes_query = "CALL db.labels() YIELD label RETURN collect(label) as labels"
            rels_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as rels"
            
            node_result = session.run(nodes_query).single()
            labels = node_result["labels"] if node_result else []
            
            rel_result = session.run(rels_query).single()
            rels = rel_result["rels"] if rel_result else []
            
            # Simple summary of graph shape
            shape_query = """
            MATCH (a)-[r]->(b)
            RETURN labels(a) AS source, type(r) AS rel_type, labels(b) AS target, count(*) as count
            ORDER BY count DESC
            """
            
            shape_result = session.run(shape_query)
            patterns = []
            for record in shape_result:
                patterns.append({
                    "source_labels": record["source"],
                    "relationship": record["rel_type"],
                    "target_labels": record["target"],
                    "occurrences": record["count"]
                })
            
            schema = {
                "node_labels": labels,
                "relationship_types": rels,
                "observed_patterns": patterns
            }
            
            print(json.dumps(schema, indent=2))
            
    except Exception as e:
        print(f"Error extracting schema: {e}")
        print("Note: The db.labels() or db.relationshipTypes() procedures might not be available depending on your Neo4j version/plugins.")
    finally:
        driver.close()

if __name__ == "__main__":
    visualize_schema()
