import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import requests

load_dotenv()

def check_neo4j():
    print("--- Checking Neo4j ---")
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    pwd = os.getenv("NEO4J_PASSWORD")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        with driver.session() as session:
            res = session.run("RETURN 'Connection Successful' as msg")
            print(f"Result: {res.single()['msg']}")
        driver.close()
    except Exception as e:
        print(f"Neo4j Connection Failed: {e}")

def check_flask():
    print("\n--- Checking Flask Server ---")
    try:
        # Just checking if the port is open/responding
        response = requests.get("http://localhost:5000/get_calendar_events")
        print(f"Flask status: {response.status_code}")
    except Exception as e:
        print("Flask server not responding. Is it running?")

if __name__ == "__main__":
    check_neo4j()
    check_flask()