import os
import sys
from pathlib import Path
from neo4j import GraphDatabase

root = Path(__file__).resolve().parent.parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from src.config import NeoConfig

# --- Configuration ---
driver = GraphDatabase.driver(NeoConfig.NEO4J_URI, auth=(NeoConfig.NEO4J_USER, NeoConfig.NEO4J_PASS))

def get_driver():
    """Establishes a connection to the Neo4j database."""
    return GraphDatabase.driver(NeoConfig.NEO4J_URI, auth=(NeoConfig.NEO4J_USER, NeoConfig.NEO4J_PASS))
