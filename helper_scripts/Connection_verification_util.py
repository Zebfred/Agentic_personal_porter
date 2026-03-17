import sys
import os
import requests
from neo4j import GraphDatabase

# Ensure we can import from the src directory when running from helper_scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import Config

def test_neo4j_connection():
    """Attempts to connect to Neo4j and run a basic verification query."""
    print("✨ Attempting to connect to Neo4j...")
    
    try:
        # Initialize the driver using your gorgeous Config class
        driver = GraphDatabase.driver(Config.NEO4J_URI, auth=(Config.NEO4J_USER, Config.NEO4J_PASS))
        
        # Open a session and run a simple test query
        with driver.session() as session:
            result = session.run("RETURN 'Connection Successful!' AS message")
            message = result.single()["message"]
            print(f"✅ Success! Database responded with: {message}")
            
    except Exception as e:
        print("❌ Oh no, darling! Could not connect to the database. Error details:")
        print(e)
    finally:
        if 'driver' in locals():
            driver.close()
            print("🔌 Connection securely closed.")

def check_flask():
    print("\n--- Checking Flask Server ---")
    try:
        # Just checking if the port is open/responding
        response = requests.get("http://localhost:5000/get_calendar_events")
        print(f"Flask status: {response.status_code}")
    except Exception as e:
        print("Flask server not responding. Is it running?")

if __name__ == "__main__":
    test_neo4j_connection()
    check_flask()