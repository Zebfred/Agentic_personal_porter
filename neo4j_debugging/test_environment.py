# This will test the environment to ensure that the .env file is set up 
# correctly and that the OpenAI and Neo4j connections are working.
import os
import unittest

from dotenv import load_dotenv, find_dotenv
load_dotenv()

class TestEnvironment(unittest.TestCase):

    skip_env_variable_tests = True
    skip_groq_test = True
    skip_neo4j_test = True

    def test_env_file_exists(self):
        env_file_exists = True if find_dotenv() > "" else False
        if env_file_exists:
            TestEnvironment.skip_env_variable_tests = False
        self.assertTrue(env_file_exists, ".env file not found.")

    def env_variable_exists(self, variable_name):
        self.assertIsNotNone(
            os.getenv(variable_name),
            f"{variable_name} not found in .env file")

    def test_qroq_variables(self):
        if TestEnvironment.skip_env_variable_tests:
            self.skipTest("Skipping GROQ env variable test")

        self.env_variable_exists('GROQ_API_KEY')
        TestEnvironment.skip_openai_test = False

    def test_neo4j_variables(self):
        if TestEnvironment.skip_env_variable_tests:
            self.skipTest("Skipping Neo4j env variables test")

        self.env_variable_exists('NEO4J_URI')
        self.env_variable_exists('NEO4J_USERNAME')
        self.env_variable_exists('NEO4J_PASSWORD')
        TestEnvironment.skip_neo4j_test = False

    def test_groq_connection(self):
        if TestEnvironment.skip_qroq_test:
            self.skipTest("Skipping OpenAI test")

        try:

            # Initialize the Groq client. It will automatically use the GROQ_API_KEY
            from groq import Groq
            # from your .env file.
            client = Groq()

            # Fetch the list of models
            models_response = client.models.list()
            
            # The actual list of model objects is in the 'data' attribute
            model_list = models_response.data
            
            if model_list:
                print("\nSuccessfully retrieved available models:")
                
                # Prepare a list of model IDs
                model_ids = [model.id for model in model_list]
                
                # Print models to the console
                for model_id in model_ids:
                    print(f"- {model_id}")
                    
                # Write the list to a text file for easy reference
                with open("available_models.txt", "w") as f:
                    f.write("Available Groq Models:\n")
                    for model_id in model_ids:
                        f.write(f"- {model_id}\n")
                
                print("\nList of models has been saved to 'available_models.txt'")
            else:
                print("API call successful, but no models were returned.")

        except AuthenticationError as e:
            models = None
        self.assertIsNotNone(
            models,
            "GROQ connection failed. Check the QROQ_API_KEY key in .env file.")

    def test_neo4j_connection(self):
        if TestEnvironment.skip_neo4j_test:
            self.skipTest("Skipping Neo4j connection test")

        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USERNAME'), 
                  os.getenv('NEO4J_PASSWORD'))
        )
        try:
            driver.verify_connectivity()
            connected = True
        except Exception as e:
            connected = False

        driver.close()

        self.assertTrue(
            connected,
            "Neo4j connection failed. Check the NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD values in .env file."
            )
        
def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestEnvironment('test_env_file_exists'))
    suite.addTest(TestEnvironment('test_qroq_variables'))
    suite.addTest(TestEnvironment('test_neo4j_variables'))
    suite.addTest(TestEnvironment('test_groq_connection'))
    suite.addTest(TestEnvironment('test_neo4j_connection'))
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
    