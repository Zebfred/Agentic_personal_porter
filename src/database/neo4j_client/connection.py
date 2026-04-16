import os
import sys
from pathlib import Path
from neo4j import GraphDatabase

root = Path(__file__).resolve().parent.parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from src.config import NeoConfig

# --- Configuration ---
# Create a singleton driver instance to enable connection pooling.
# The driver maintains a pool of connections. Creating a new driver per request
# defeats connection pooling and is a massive performance bottleneck.
_driver_instance = None

def get_driver():
    """Returns a singleton connection driver to the Neo4j database, utilizing connection pooling."""
    global _driver_instance
    if _driver_instance is None:
        _driver_instance = GraphDatabase.driver(
            NeoConfig.NEO4J_URI,
            auth=(NeoConfig.NEO4J_USER, NeoConfig.NEO4J_PASS)
        )
    return _driver_instance
