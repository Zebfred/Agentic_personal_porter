from neo4j import GraphDatabase

import os
import unittest
os.environ["PYTHONNEO4JDEBUG"] = "1"

from dotenv import load_dotenv, find_dotenv
load_dotenv()

# Replace with your server details
#uri = -
#username = -
#password = -
# --- Database Connection ---
uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

if not all([uri, username, password]):
    raise ValueError("Missing one or more Neo4j environment variables.")

# Create a driver object
driver = GraphDatabase.driver(uri, auth=(username, password))

# Verify connectivity
driver.verify_connectivity()
print("Connection established successfully.")

# Example query
def create_node(tx):
    tx.run("CREATE (:Message {text: 'Hello from Python!'})")

with driver.session() as session:
    session.execute_write(create_node)

driver.close()
