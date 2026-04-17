#OUTDATED, but might prove useful for something else
from pymongo import MongoClient
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings # Or your preferred embedding model

# 1. Initialize the "Librarian" (Vector DB Connection)
client = MongoClient("YOUR_GCP_MONGODB_URI")
collection = client["Porter"]["Intuitive_Memory"]
embeddings = OpenAIEmbeddings(model="text-embedding-3-small") # Efficient for 1GB limits

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