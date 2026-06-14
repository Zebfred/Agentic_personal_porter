import os
import logging
from datetime import datetime
from typing import Optional, TypedDict, Dict, Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END


from src.utils.path_utils import load_env_vars, get_auth_file
from src.database.mongo_storage import SovereignMongoStorage
from src.utils.token_circuit_breaker import TokenLimitExceededError
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
    import json
    import asyncio
    from google.adk.agents.llm_agent import Agent
    from google.adk.runners import InMemoryRunner
    from google.adk.models.lite_llm import LiteLlm
    from google.genai import types
    
    logger.info("Categorizer Node: Using ADK LlmAgent (Llama 3.3 70b)")
    
    adk_model = LiteLlm(model="groq/llama-3.3-70b-versatile")
    agent = Agent(
        name="The_Categorizer",
        model=adk_model,
        instruction="You are 'The Categorizer'. You are no longer a deep contextual philosophical coach. Your sole responsibility is to evaluate daily events and definitively map them to exactly one of the designated 9 Hero Pillars (e.g. Health, Wealth, Core). Fast, objective, and strict.\n\nGoal: Perform strict, low-latency categorization of Intention vs. Actual events across the 9 Core Pillars.\n\nIMPORTANT: Your output MUST be ONLY a raw JSON block with the following keys:\n- 'Pillar': Name of the Pillar (e.g. '1. Core Identity')\n- 'Reason': 1-sentence strict analytical reason\n- 'Confidence_Score': integer from 0 to 100\nDo not include markdown tags like ```json."
    )
    
    query = f"1. Analyze the following FRONTEND PAYLOAD quickly submitted by {state['username']}:\n'{state['journal_entry']}'\n\n2. Contextualize it against his last 5 Calendar Events:\n{state['actuals_str']}\n\n3. Identify EXACTLY which of the 9 Hero pillars this combination represents."
    
    runner = InMemoryRunner(agent=agent, app_name="porter")
    
    async def run_adk():
        session = await runner.session_service.create_session(app_name="porter", user_id="porter_user")
        user_msg = types.Content(role="user", parts=[types.Part(text=query)])
        
        final_text = ""
        total_tokens = 0
        from src.utils.token_circuit_breaker import TokenLimitExceededError
        
        for response in runner.run(user_id="porter_user", session_id=session.id, new_message=user_msg):
            # ADK Token Circuit Breaker Logic
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                total_tokens += getattr(response.usage_metadata, 'total_token_count', 0)
                if total_tokens > 25000:
                    logger.error(f"[CIRCUIT BROKEN] Categorizer exceeded 25000 tokens! Total used: {total_tokens}. Force halting.")
                    raise TokenLimitExceededError("Agent trapped in hallucination loop. Exceeded API safety cap of 25000 tokens.")
            
            if hasattr(response, 'content') and response.content and response.content.parts:
                for part in response.content.parts:
                    if hasattr(part, 'text') and part.text:
                        if getattr(response, 'author', '') == agent.name:
                            final_text = part.text
        return final_text
    
    result_text = asyncio.run(run_adk())
    
    # Parse the returned JSON
    result_text = result_text.replace('```json', '').replace('```', '').strip()
    try:
        data = json.loads(result_text)
        recon_str = f"```json\n{{\n  \"Pillar\": \"{data.get('Pillar', 'Unknown')}\",\n  \"Reason\": \"{data.get('Reason', '')}\",\n  \"Confidence_Score\": {data.get('Confidence_Score', 0)}\n}}\n```"
    except Exception as e:
        recon_str = f"```json\n{{\n  \"Pillar\": \"Parse Error\",\n  \"Reason\": \"Failed to parse ADK Categorizer response: {str(e)}\",\n  \"Confidence_Score\": 0\n}}\n```"
        
    return {"recon_result": recon_str}

def should_curate(state: ReflectionState) -> str:
    log_data = state.get("log_data")
    if log_data and log_data.get('isValuableDetour'):
        return "curator_node"
    return "save_results_node"

def curator_node(state: ReflectionState) -> ReflectionState:
    import asyncio
    from google.adk.agents.llm_agent import Agent
    from google.adk.runners import InMemoryRunner
    from google.adk.models.lite_llm import LiteLlm
    from google.genai import types
    
    logger.info("Curator Node: Using ADK LlmAgent (Llama 3.3 70b)")
    
    adk_model = LiteLlm(model="groq/llama-3.3-70b-versatile")
    agent = Agent(
        name="GTKY_Librarian",
        model=adk_model,
        instruction="You are 'GTKY Librarian (The Curator of Truth)'. Your duty is fidelity. When ingesting GCal data, look for 'The Fog of War' (unlabeled blocks). Your goal isn't to judge, but to provide The Categorizer with the most accurate 'Actuals' possible.\n\nGoal: Identify 'The Fog of War' in daily logs and log 'Valuable Detours' to the User Inventory."
    )
    
    log_data = state.get("log_data") or {}
    inventory_note = log_data.get('inventoryNote', 'Gained unforeseen experience.')
    
    query = f"{state['username']} has declared the recent activity a 'Valuable Detour'.\nHis note: '{inventory_note}'\nEvaluate this new 'acquired skill' against his overall Origin Story.\nExpected output: A concise 2-sentence summary of the new skill appended to the end of the Recon Report under an 'Acquired Inventory' header."
    
    runner = InMemoryRunner(agent=agent, app_name="porter")
    
    async def run_adk():
        session = await runner.session_service.create_session(app_name="porter", user_id="porter_user")
        user_msg = types.Content(role="user", parts=[types.Part(text=query)])
        
        final_text = ""
        total_tokens = 0
        from src.utils.token_circuit_breaker import TokenLimitExceededError
        
        for response in runner.run(user_id="porter_user", session_id=session.id, new_message=user_msg):
            # ADK Token Circuit Breaker Logic
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                total_tokens += getattr(response.usage_metadata, 'total_token_count', 0)
                if total_tokens > 25000:
                    logger.error(f"[CIRCUIT BROKEN] Curator exceeded 25000 tokens! Total used: {total_tokens}. Force halting.")
                    raise TokenLimitExceededError("Agent trapped in hallucination loop. Exceeded API safety cap of 25000 tokens.")
            
            if hasattr(response, 'content') and response.content and response.content.parts:
                for part in response.content.parts:
                    if hasattr(part, 'text') and part.text:
                        if getattr(response, 'author', '') == agent.name:
                            final_text = part.text
        return final_text
    
    result_text = asyncio.run(run_adk())
    
    curator_str = f"### Acquired Inventory\n{result_text}"
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
        logger.info(f"\n--- Recon Complete. Report saved to {out_file} and MongoDB ---")
    except Exception as e:
        logger.info(f"\n--- Recon Complete. Report saved to {out_file}. MongoDB save failed: {e} ---")
        
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
    
    logger.info("--- Starting Sovereign Daily Recon ---")
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
        logger.info(f"\n[CRITICAL RUNTIME ERROR] {e}")
        health_manager.end_agent_run(run_id, status="fail", error_msg=str(e))
        return "ERROR: Socratic Categorizer experienced a logic loop and was forcefully halted by the Token Circuit Breaker to preserve API limits."
    except Exception as e:
        logger.info(f"\n[RUNTIME ERROR] {e}")
        health_manager.end_agent_run(run_id, status="fail", error_msg=str(e))
        return f"ERROR: Unexpected Backend Error during Categorization: {e}"

if __name__ == "__main__":
    # Test execution
    sample_journal = "Intention: Work deeply. Actual: Fell down a rabbit hole of tutorials and abstract thought."
    logger.info(run_porter_reflection(sample_journal))
