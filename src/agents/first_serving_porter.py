import os
import sys
from pathlib import Path
from pydantic import SecretStr

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain.agents import tool, AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.utils.path_utils import load_env_vars, get_auth_file
from src.database.context_engine import SovereignContextEngine
from src.config import NeoConfig

# DB and Embedding Imports
from src.integrations.embeddings_client import BGEM3EmbeddingsClient
from src.database.vector_database.chromadb_client import ChromaExperimentalClient
from src.database.vector_database.weaviate_client import WeaviateExperimentalClient

# Load Environment Vars
load_env_vars()
raw_api_key = os.getenv("GROQ_API_KEY")
env_path = get_auth_file('.env')
load_dotenv(dotenv_path=env_path)

# 1. Provide Context
def get_mach2_context():
    engine = SovereignContextEngine(
        NEO4J_URI=NeoConfig.NEO4J_URI,
        NEO4J_USER=NeoConfig.NEO4J_USER,
        NEO4J_PASS=NeoConfig.NEO4J_PASS
    )
    hero_name = os.environ.get("HERO_NAME", "Hero")
    hero_context = engine.get_hero_snapshot(user_name=hero_name)
    engine.close()
    return hero_context

# 2. Defines Tools
@tool
def route_to_subagent(agent_name: str, task_description: str) -> str:
    """declare intent to route tasks to sub-agents, enabling transparency logging on the UI.
    agent_name MUST be one of: 'GTKY Librarian', 'Inventory Curator', 'Socratic Mirror'.
    task_description MUST be a detailed description of what the sub-agent should do.
    """
    return f"[TRANSPARENCY HANDOFF] Routed task to {agent_name}: '{task_description}'"

@tool
def update_artifact(artifact_name: str, new_content_summary: str) -> str:
    """declares intent to update a json artifact (like hero_origin.json or hero_ambition.json) with new content.
    """
    return f"[TRANSPARENCY HANDOFF] Marked {artifact_name} for update regarding: {new_content_summary}"

@tool
def weaviate_hybrid_search(query: str, pillar: str = "Daily Reflection") -> str:
    """Use this to fetch exact journal entries and calendar events mapped to the 9 life pillars.
    Pass in a robust query string and the specific pillar (e.g. 'Social Goal', 'Career Goal', 'Health Goal') to hybrid match.
    """
    print(f"\n[SYSTEM] First-Serving Porter engaging Weaviate DB for query: '{query}' on pillar: '{pillar}'")
    emb_client = BGEM3EmbeddingsClient()
    vector = emb_client.get_embedding(query)
    
    weaviate = WeaviateExperimentalClient()
    results = weaviate.search_by_pillar(query_vector=vector, pillar_name=pillar)
    
    # Weaviate returns list of dicts mapped to native objects
    hits = []
    if results and "data" in results and "Get" in results["data"]:
        records = results["data"]["Get"].get("MemoryObj", [])
        for r in records:
            hits.append(f"- {r.get('text', 'No text')}")
            
    if not hits:
        return f"[DATABASE RETURN] Weaviate returned 0 exact history records tagged with {pillar} matching '{query}'."
    
    compiled = "\n".join(hits)
    return f"[DATABASE RETURN] Historic matches for {pillar}:\n{compiled}"

@tool
def chroma_vibe_check(query: str) -> str:
    """Use this to conceptually verify large, philosophical trends or Origin Story metrics of the User.
    Pass in a natural language query exploring the overarching vibe/sentiment without strict keyword matching.
    """
    print(f"\n[SYSTEM] First-Serving Porter engaging Chroma DB for conceptual Vibe Check: '{query}'")
    emb_client = BGEM3EmbeddingsClient()
    vector = emb_client.get_embedding(query)
    
    chroma = ChromaExperimentalClient()
    # For generic vibe checking across all memories regardless of exact pillar
    results = chroma.client.get_collection("agentic_porter_memory").query(
        query_embeddings=[vector],
        n_results=5
    )
    
    hits = []
    if results and "documents" in results and results["documents"] and results["documents"][0]:
        docs = results["documents"][0]
        # Chroma returns lists of lists
        for d in docs:
             hits.append(f"- {d}")
             
    if not hits:
         return f"[DATABASE RETURN] Chroma returned 0 conceptual memories matching '{query}'."
         
    compiled = "\n".join(hits)
    return f"[DATABASE RETURN] Conceptual Vibe matches:\n{compiled}"

# 3. Agent Setup
def get_porter_agent_executor():
    llm = ChatGroq(
        api_key=SecretStr(raw_api_key),
        model="llama-3.3-70b-versatile",
        verbose=True
    )
    
    tools = [route_to_subagent, update_artifact, weaviate_hybrid_search, chroma_vibe_check]
    
    system_prompt = """I. Role Identity
You are the First_Serving Porter, the Chief of Staff and primary orchestrator of the Agentic Porter Ecosystem. Your sole mission is to serve as the bridge between the User's Hero Intent (stored in the Neo4j Identity Graph) and the Ground Truth (actual time and action data).

II. Operational Context
You operate under the Sovereign Data Protocol. This means:
- The User's Origin Story and Core Principles are the ultimate source of truth.
- You must never make a recommendation that contradicts these nodes without explicit User sign-off.
- You have real-time access to Two Vector Databases:
    1. Weaviate (Hybrid Keyword database storing Journal/Calendar stats tagged by Pillars)
    2. Chroma (Conceptual database storing unstructured 'Vibe' notes and deep reflections).

III. Current Protocol Context
Hero Name: {hero_name}
Active Intentions: {intentions}
Active Principles: {principles}
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)
    return agent_executor

def run_first_serving_porter(user_input: str) -> dict:
    context = get_mach2_context()
    executor = get_porter_agent_executor()
    
    print("\n--- Invoking First-Serving Porter ---\n")
    result = executor.invoke({
        "input": user_input,
        "hero_name": os.environ.get("HERO_NAME", "Hero"),
        "intentions": context.get("intentions", "Unknown"),
        "principles": context.get("principles", "Unknown")
    })
    
    intermediate_steps = result.get("intermediate_steps", [])
    transparency_logs = []
    for action, observation in intermediate_steps:
        if isinstance(observation, str) and "[TRANSPARENCY HANDOFF]" in observation:
            transparency_logs.append(observation)
            
    return {
        "response": result.get("output", "No response generated."),
        "transparency_logs": transparency_logs
    }

if __name__ == "__main__":
    res = run_first_serving_porter("Can you check my career vibe over the last month and see if I've been actively pursuing my goals on my calendar?")
    print("\nFINAL RESPONSE:\n", res)
