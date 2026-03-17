from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import sys
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.auth', '.env'))

# Ensure we can import from the src directory when running from helper_scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import Config

# Replace the placeholder with your Atlas connection string
uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")  # Default to local MongoDB if MONGO_URI is not set

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
   client.admin.command('ping')
   print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
   print(e)