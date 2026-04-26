# OUTDATED: Note that this file contains module-level code (lines 14-23) that executes on import.
# This causes an import-time side effect (connection hang) if accidentally imported.
# Kept for reference.
from pymongo import MongoClient
from langchain_mongodb import MongoDBAtlasVectorSearch

class LocalBGEM3Wrapper:
    def __init__(self):
        from src.integrations.embeddings_client import BGEM3EmbeddingsClient
        self.client = BGEM3EmbeddingsClient()
    def embed_documents(self, texts):
        return self.client.get_embeddings_batch(texts)
    def embed_query(self, text):
        return self.client.get_embedding(text)

# 1. Initialize the "Librarian" (Vector DB Connection)
client = MongoClient("YOUR_GCP_MONGODB_URI")
collection = client["Porter"]["Intuitive_Memory"]
embeddings = LocalBGEM3Wrapper()

vector_store = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name="hero_xp_index"
)

# 2. The Memory Query Logic
def get_curator_context(new_task_description):
    """
    Finds the top 3 most relevant 'past achievements' to provide 
    context for the current 'Inventory' update.
    """
    # We search for 'Similar Vibes' in the Hero's history
    # This is the 'Intuitive' part—finding patterns, not keywords.
    docs = vector_store.similarity_search(
        query=new_task_description,
        k=3,
        pre_filter={"life_pillar": {"$eq": "Professional-growth"}} # Meta-data filtering!
    )
    
    return [doc.page_content for doc in docs]

# 3. Usage by the Agent
current_event = "Refined the Groq API error handling for the multi-agent loop."
past_context = get_curator_context(current_event)

# Result: The Agent now knows the Hero has 4 prior entries on 'API Resilience'.
# It can now upgrade the Hero's 'Systems Architect' skill node in Neo4j!