import os
from pathlib import Path
from dotenv import load_dotenv

# Find root and load .env once
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".auth" / ".env")

class Config:
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USER = os.getenv("NEO4J_USERNAME")
    NEO4J_PASS = os.getenv("NEO4J_PASSWORD")