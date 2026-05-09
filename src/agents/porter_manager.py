import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, TypedDict, Dict, Any

from dotenv import load_dotenv
from pydantic import SecretStr, BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.utils.llm_factory import AgentLLMConfig
sys.path.append(str(root))

from src.utils.path_utils import load_env_vars, get_auth_file
from src.database.context_engine import SovereignContextEngine
from src.config import NeoConfig
from src.database.mongo_storage import SovereignMongoStorage
from src.utils.token_circuit_breaker import TokenCircuitBreakerHandler, TokenLimitExceededError
from src.database.mongo_client.agent_health import AgentHeartbeatManager
from src.agents.context_loader import get_context

load_env_vars()
raw_api_key = os.getenv("GROQ_API_KEY")
env_path = get_auth_file('.env')
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# State definition
class ReflectionState(TypedDict, total=False):
    journal_entry: str
    log_data: Optional[Dict[str, Any]]
    username: str
    actuals_str: str
    recon_result: str
    curator_result: str
    final_output: str

# Structured output for Categorizer
class CategorizationResult(BaseModel):
    Pillar: str = Field(description="Name of the Pillar (1. Core Identity, 2. Mind, 3. Body/Health, 4. Heart/Social, 5. Wealth/Career, 6. Community, 7. Leisure, 8. Spirit, 9. Duty)")
    Reason: str = Field(description="1-sentence strict analytical reason")
    Confidence_Score: int = Field(description="an integer from 0 to 100 representing how certain you are of this pillar mapping")

# Node Functions
def setup_node(state: ReflectionState) -> ReflectionState:
    logger.info("Initializing Agentic Porter Sovereign Sync (LangGraph)...")
    username = state["username"]
    hero_context = get_context(username=username)
    
    # Fetching Ground Truth Data for the Recon Task
    storage = SovereignMongoStorage()
    mongo_actuals = list(storage.formatted_col.find({"record_type": "Actual"}).sort("start", -1).limit(5))
    actuals_str = "\n".join([f"- {e.get('title', 'Unknown')} ({e.get('pillar', 'Uncategorized')})" for e in mongo_actuals])
    if not actuals_str:
        actuals_str = "No recent actual events found."
        
    return {"actuals_str": actuals_str}

def categorizer_node(state: ReflectionState) -> ReflectionState:
    breaker = TokenCircuitBreakerHandler(max_tokens=25000)
    config = AgentLLMConfig(provider="groq", model="llama-3.1-8b-instant")
    llm = config.get_chat_model(
        verbose=True,
        callbacks=[breaker]
    ).with_structured_output(CategorizationResult)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are 'The Categorizer'. You are no longer a deep contextual philosophical coach. Your sole responsibility is to evaluate daily events and definitively map them to exactly one of the designated 9 Hero Pillars (e.g. Health, Wealth, Core). Fast, objective, and strict.\n\nGoal: Perform strict, low-latency categorization of Intention vs. Actual events across the 9 Core Pillars."),
        ("user", "1. Analyze the following FRONTEND PAYLOAD quickly submitted by {username}:\n'{journal_entry}'\n\n2. Contextualize it against his last 5 Calendar Events:\n{actuals_str}\n\n3. Identify EXACTLY which of the 9 Hero pillars this combination represents: (1. Core Identity, 2. Mind, 3. Body/Health, 4. Heart/Social, 5. Wealth/Career, 6. Community, 7. Leisure, 8. Spirit, 9. Duty).\nExpected output: A single structured JSON block.")
    ])
    
    chain = prompt | llm
    result = chain.invoke({
        "username": state["username"],
        "journal_entry": state["journal_entry"],
        "actuals_str": state["actuals_str"]
    })
    
    assert isinstance(result, CategorizationResult)
    # Format the result to match the old crew output roughly
    recon_str = f"```json\n{{\n  \"Pillar\": \"{result.Pillar}\",\n  \"Reason\": \"{result.Reason}\",\n  \"Confidence_Score\": {result.Confidence_Score}\n}}\n```"
    
    return {"recon_result": recon_str}

def should_curate(state: ReflectionState) -> str:
    log_data = state.get("log_data")
    if log_data and log_data.get('isValuableDetour'):
        return "curator_node"
    return "save_results_node"

def curator_node(state: ReflectionState) -> ReflectionState:
    breaker = TokenCircuitBreakerHandler(max_tokens=25000)
    config = AgentLLMConfig(provider="groq", model="llama-3.1-8b-instant")
    llm = config.get_chat_model(
        verbose=True,
        callbacks=[breaker]
    )
    
    log_data = state.get("log_data") or {}
    inventory_note = log_data.get('inventoryNote', 'Gained unforeseen experience.')
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are 'GTKY Librarian (The Curator of Truth)'. Your duty is fidelity. When ingesting GCal data, look for 'The Fog of War' (unlabeled blocks). Your goal isn't to judge, but to provide The Categorizer with the most accurate 'Actuals' possible.\n\nGoal: Identify 'The Fog of War' in daily logs and log 'Valuable Detours' to the User Inventory."),
        ("user", "{username} has declared the recent activity a 'Valuable Detour'.\nHis note: '{inventory_note}'\nEvaluate this new 'acquired skill' against his overall Origin Story.\nExpected output: A concise 2-sentence summary of the new skill appended to the end of the Recon Report under an 'Acquired Inventory' header.")
    ])
    
    chain = prompt | llm
    result = chain.invoke({
        "username": state["username"],
        "inventory_note": inventory_note
    })
    
    curator_str = f"### Acquired Inventory\n{result.content}"
    return {"curator_result": curator_str}

def save_results_node(state: ReflectionState) -> ReflectionState:
    recon_result = state.get("recon_result", "")
    curator_result = state.get("curator_result", "")
    
    final_output = recon_result
    if curator_result:
        final_output += f"\n\n{curator_result}"
        
    current_date = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "reflections")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"daily_recon_{current_date}.md")
    
    with open(out_file, "w") as f:
        f.write(f"# Sovereign Agent: Daily Reconnaissance ({current_date})\n\n")
        f.write(final_output)
        
    storage = SovereignMongoStorage()
    try:
        reflection_data = {
            "day": current_date,
            "user_id": state["username"],
            "reflection_text": final_output,
            "metadata": {
                "journal_entry": state["journal_entry"],
                "log_data": state["log_data"]
            }
        }
        storage.save_agent_reflection(reflection_data)
        print(f"\n--- Recon Complete. Report saved to {out_file} and MongoDB ---")
    except Exception as e:
        print(f"\n--- Recon Complete. Report saved to {out_file}. MongoDB save failed: {e} ---")
        
    return {"final_output": final_output}

# Build Graph
builder = StateGraph(ReflectionState)
builder.add_node("setup_node", setup_node)
builder.add_node("categorizer_node", categorizer_node)
builder.add_node("curator_node", curator_node)
builder.add_node("save_results_node", save_results_node)

builder.add_edge(START, "setup_node")
builder.add_edge("setup_node", "categorizer_node")
builder.add_conditional_edges("categorizer_node", should_curate, ["curator_node", "save_results_node"])
builder.add_edge("curator_node", "save_results_node")
builder.add_edge("save_results_node", END)

graph = builder.compile()

def run_porter_reflection(journal_entry: str, log_data: dict | None = None, username: str = "Hero") -> str:
    """
    Executes the Sovereign Socratic Reflection Pipeline using LangGraph.
    Combines Frontend 'Intention/Actual' payload with Graph Context.
    """
    health_manager = AgentHeartbeatManager()
    run_id = health_manager.start_agent_run("mach_3_graph", {"journal_entry": journal_entry})
    
    print("--- Starting Sovereign Daily Recon ---")
    try:
        initial_state: ReflectionState = {
            "journal_entry": journal_entry,
            "log_data": log_data,
            "username": username,
            "actuals_str": "",
            "recon_result": "",
            "curator_result": "",
            "final_output": ""
        }
        result = graph.invoke(initial_state)
        final_text = result["final_output"]
        health_manager.end_agent_run(run_id, status="success")
        return final_text
    except TokenLimitExceededError as e:
        print(f"\n[CRITICAL RUNTIME ERROR] {e}")
        health_manager.end_agent_run(run_id, status="fail", error_msg=str(e))
        return "ERROR: Socratic Categorizer experienced a logic loop and was forcefully halted by the Token Circuit Breaker to preserve API limits."
    except Exception as e:
        print(f"\n[RUNTIME ERROR] {e}")
        health_manager.end_agent_run(run_id, status="fail", error_msg=str(e))
        return f"ERROR: Unexpected Backend Error during Categorization: {e}"

if __name__ == "__main__":
    # Test execution
    sample_journal = "Intention: Work deeply. Actual: Fell down a rabbit hole of tutorials and abstract thought."
    print(run_porter_reflection(sample_journal))
