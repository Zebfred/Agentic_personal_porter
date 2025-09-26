from neo4j import GraphDatabase

# Replace with your server details
uri = -
username = -
password = -

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
