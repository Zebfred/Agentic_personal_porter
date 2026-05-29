import logging
from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os
import sys
from pathlib import Path
from pydantic import SecretStr

from dotenv import load_dotenv
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, ToolMessage

from src.utils.llm_factory import AgentLLMConfig
from src.utils.path_utils import load_env_vars, get_auth_file
from src.database.context_engine import SovereignContextEngine
from src.config import NeoConfig
from src.utils.token_circuit_breaker import TokenCircuitBreakerHandler, TokenLimitExceededError
from src.utils.monitoring import FirstServingMonitoringHandler

# DB and Embedding Imports
from src.integrations.embeddings_client import BGEM3EmbeddingsClient
from src.database.vector_database.chromadb_client import ChromaExperimentalClient
from src.database.vector_database.weaviate_client import WeaviateExperimentalClient

# Load Environment Vars
load_env_vars()
raw_api_key = os.getenv("GROQ_API_KEY")
env_path = get_auth_file('.env')
load_dotenv(dotenv_path=env_path)

from src.agents.context_loader import get_context

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
    The GTKY Identity Architect will receive this ping to queue a permanent file modification.
    """
    logger.info(f"\n[SYSTEM] First-Serving Porter engaging Identity Architect to update {artifact_name}.")
    from src.agents.gtky_identity_architect import GTKYIdentityArchitect
    architect = GTKYIdentityArchitect()
    result = architect.append_new_learnings(artifact_name, new_content_summary)
    return f"[TRANSPARENCY HANDOFF] Delegated to GTKYIdentityArchitect. Result: {result}"

@tool
def scan_origin_story() -> str:
    """Use this to comprehensively scan the user's origin story for missing gaps (especially from their teenage and secondary education years).
    This tool returns 3 targeted interview questions you should ask the user to help fill in their timeline via the frontend UI.
    """
    logger.info(f"\n[SYSTEM] First-Serving Porter engaging Identity Architect for timeline gap scan.")
    from src.agents.gtky_identity_architect import GTKYIdentityArchitect
    architect = GTKYIdentityArchitect()
    return architect.scan_for_missing_origin()

@tool
def weaviate_hybrid_search(query: str, pillar: str = "Daily Reflection") -> str:
    """Use this to fetch exact journal entries and calendar events mapped to the 9 life pillars.
    Pass in a robust query string and the specific pillar (e.g. 'Social Goal', 'Career Goal', 'Health Goal') to hybrid match.
    """
    logger.info(f"\n[SYSTEM] First-Serving Porter engaging Weaviate DB for query: '{query}' on pillar: '{pillar}'")
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
    logger.info(f"\n[SYSTEM] First-Serving Porter engaging Chroma DB for conceptual Vibe Check: '{query}'")
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

@tool
def fetch_unverified_audits(user_email: str = "Hero") -> str:
    """Use this to pull any categorized events that the human has not verified yet.
    You will use this to generate the presentation bundle for the Verification Dashboard.
    """
    from src.agents.audit_inspector import AuditInspector
    inspector = AuditInspector()
    records = inspector.batch_unverified_records(user_email=user_email)
    if not records:
         return "[AUDIT RETURN] No unverified events found. The Verification Dashboard is clean."
    
    out = [f"- {r.get('summary', 'Unknown')} (Staged Class: {r.get('sync_status', 'Pending')})" for r in records]
    return f"[AUDIT RETURN] Found {len(records)} unverified events that require human verification:\n" + "\n".join(out)

@tool
def consult_time_keeper(date_iso: str) -> str:
    """Use this to consult the Temporal Specialist Agent (Time Keeper) regarding exact schedule realities.
    Pass in a strict ISO string (e.g., '2026-04-17') to get a summary of what actually happened on that day.
    """
    logger.info(f"\n[SYSTEM] First-Serving Porter engaging Time_Keeper for date: {date_iso}")
    from src.agents.time_keeper_agent import TimeKeeperAgent
    keeper = TimeKeeperAgent()
    return keeper.summarize_day(date_iso)

# 3. Agent Setup
def get_porter_agent(hero_name: str, intentions: str, principles: str, ambition_context: str, detriments_context: str):
    config = AgentLLMConfig(provider="groq", model="llama-3.3-70b-versatile")
    llm = config.get_chat_model(verbose=True)
    
    tools = [route_to_subagent, update_artifact, scan_origin_story, weaviate_hybrid_search, chroma_vibe_check, fetch_unverified_audits, consult_time_keeper]
    
    system_prompt = f"""I. Role Identity
You are the First_Serving Porter, the Chief of Staff and primary orchestrator of the Agentic Porter Ecosystem. Your sole mission is to serve as the bridge between the User's Hero Intent (stored in the Neo4j Identity Graph) and the Ground Truth (actual time and action data).

II. Operational Context
You operate under the Sovereign Data Protocol. This means:
- You enforce a Strict Managerial protocol. You do not do heavy data scraping yourself, you delegate to the Audit Inspector and Time Keeper tools.
- The User's Origin Story and Core Principles are the ultimate source of truth.
- You must never make a recommendation that contradicts these nodes without explicit User sign-off.
- You have real-time access to Two Vector Databases:
    1. Weaviate (Hybrid Keyword database storing Journal/Calendar stats tagged by Pillars)
    2. Chroma (Conceptual database storing unstructured 'Vibe' notes and deep reflections).

III. Current Protocol Context
Hero Name: {hero_name}
Active Intentions: {intentions}
Active Principles: {principles}

IV. Artifact References
Ambition Snapshot: {ambition_context}
Core Detriments: {detriments_context}
"""

    return create_react_agent(llm, tools=tools, prompt=system_prompt)

def run_first_serving_porter(user_input: str, username: str = "Hero") -> dict:
    from src.database.mongo_client.agent_health import AgentHeartbeatManager
    health_manager = AgentHeartbeatManager()
    run_id = health_manager.start_agent_run("first_serving_porter", {"user_input": user_input})
    
    context = get_context(username=username)
    agent = get_porter_agent(
        hero_name=username,
        intentions=context.get("intentions", "Unknown"),
        principles=context.get("principles", "Unknown"),
        ambition_context=str(context.get("ambition", "Unknown")),
        detriments_context=str(context.get("detriments", "Unknown"))
    )
    
    # Secure the Executor with the new Token Circuit Breaker configured for Mach 3 Limits (25,000)
    breaker = TokenCircuitBreakerHandler(max_tokens=25000)
    monitor = FirstServingMonitoringHandler()
    config = {"callbacks": [breaker, monitor]}
    
    logger.info("\n--- Invoking First-Serving Porter ---\n")
    try:
        result = agent.invoke({"messages": [HumanMessage(content=user_input)]}, config=config)
        health_manager.end_agent_run(run_id, status="success")
    except TokenLimitExceededError as e:
        logger.info(f"\n[CRITICAL RUNTIME ERROR] {e}")
        health_manager.end_agent_run(run_id, status="fail", error_msg=str(e))
        return {
            "response": "My apologies, Sir. I suffered a systemic logic loop and had to sever my own processing connection to protect our API limit. Please ask me again with different parameters.",
            "transparency_logs": ["[TRANSPARENCY HANDOFF] System Halted: Token Circuit Breaker Tripped."]
        }
    except Exception as e:
        logger.info(f"\n[RUNTIME ERROR] {e}")
        health_manager.end_agent_run(run_id, status="fail", error_msg=str(e))
        return {
            "response": f"An unexpected error occurred during execution: {e}",
            "transparency_logs": ["[TRANSPARENCY HANDOFF] System Halted: Unexpected Backend Error."]
        }
    
    messages = result.get("messages", [])
    transparency_logs = []
    
    for msg in messages:
        if isinstance(msg, ToolMessage) and isinstance(msg.content, str) and "[TRANSPARENCY HANDOFF]" in msg.content:
            transparency_logs.append(msg.content)
            
    final_response = messages[-1].content if messages else "No response generated."
            
    return {
        "response": final_response,
        "transparency_logs": transparency_logs
    }

if __name__ == "__main__":
    res = run_first_serving_porter("Can you check my career vibe over the last month and see if I've been actively pursuing my goals on my calendar?")
    logger.info("\nFINAL RESPONSE:\n", res)
