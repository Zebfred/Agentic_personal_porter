import os
import unittest
from dotenv import load_dotenv, find_dotenv
from groq import Groq, AuthenticationError
from neo4j import GraphDatabase, exceptions as neo4j_exceptions

# --- The Main Event ---
# This function is our single source of truth for loading environment variables.
# It's like the bouncer at the club door, checking IDs.
def load_and_validate_env():
    """Finds and loads the .env file, returning True if successful."""
    if not find_dotenv():
        print("--- ❌ CRITICAL: .env file not found! ---")
        return False
    load_dotenv()
    return True

class TestEnvironmentConnections(unittest.TestCase):
    """A suite of tests to verify external API and database connections."""

    # We only run these tests if the .env file was actually found.
    # No point in testing connections if we don't even have the keys to the car.
    @unittest.skipIf(not load_and_validate_env(), ".env file not found, skipping all connection tests.")
    def test_all_required_variables_exist(self):
        """Checks if all necessary keys are present in the loaded .env file."""
        print("\n--- ✅ CHECKING FOR REQUIRED VARIABLES ---")
        required_vars = ['GROQ_API_KEY', 'NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD']
        missing_vars = [v for v in required_vars if not os.getenv(v)]
        self.assertEqual(len(missing_vars), 0, f"Missing required environment variables: {', '.join(missing_vars)}")
        print("All required variables are present.")

    @unittest.skipIf(not load_and_validate_env(), ".env file not found, skipping all connection tests.")
    def test_groq_connection_and_authentication(self):
        """Tests the connection to Groq's API and verifies the API key."""
        print("\n--- 🧠 TESTING GROQ API CONNECTION ---")
        try:
            # If your API key is wrong, this line will scream bloody murder.
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            client.models.list()
            print("Groq connection successful! Your API key is valid.")
            self.assertTrue(True)
        except AuthenticationError:
            self.fail("Groq AuthenticationError: Your GROQ_API_KEY is incorrect.")
        except Exception as e:
            self.fail(f"An unexpected error occurred with Groq: {e}")

    @unittest.skipIf(not load_and_validate_env(), ".env file not found, skipping all connection tests.")
    def test_neo4j_connection_and_authentication(self):
        """Tests the connection to Neo4j and verifies credentials."""
        print("\n--- 🔗 TESTING NEO4J DATABASE CONNECTION ---")
        #uri = os.getenv("NEO4J_URI")
        #user = os.getenv("NEO4J_USERNAME")
        #password = os.getenv("NEO4J_PASSWORD")
        uri = 'locally used variables'
        user = 'locally used variables'
        password = 'locally used variables'

        try:
            # If any of your credentials are wrong, this is where the bouncer throws you out.
            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            print("Neo4j connection successful! Your credentials are correct.")
            self.assertTrue(True)

            # Example query
            def create_node(tx):
                tx.run("CREATE (:Message {text: 'Hello from Python!'})")
                print("Test node created successfully in Neo4j.")

            with driver.session() as session:
                session.execute_write(create_node)
        except neo4j_exceptions.AuthError:
            self.fail("Neo4j AuthError: The NEO4J_USERNAME or NEO4J_PASSWORD is incorrect.")
        except Exception as e:
            # This catches other issues, like a bad URI.
            self.fail(f"Neo4j connection failed for a reason other than auth: {e}")
        finally:
            if 'driver' in locals() and driver:
                driver.close()

# --- How to Run This Show ---
if __name__ == '__main__':
    print("--- 🚀 KICKING OFF ENVIRONMENT VALIDATION ---")
    # This makes the test runner a bit more verbose, which is what we want for debugging.
    # It's like asking the bouncer to announce who's getting in and who's getting tossed.
    unittest.main(verbosity=2)
