import os
import sys
from pathlib import Path
from pydantic import SecretStr
from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from langchain_groq import ChatGroq
from langchain.agents import tool, AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from src.utils.path_utils import load_env_vars, get_auth_file
from src.database.context_engine import SovereignContextEngine
from src.config import NeoConfig

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

# 3. Agent Setup
def get_porter_agent_executor():
    llm = ChatGroq(
        api_key=SecretStr(raw_api_key),
        model="groq/llama-3.3-70b-versatile",
        verbose=True
    )
    
    tools = [route_to_subagent, update_artifact]
    
    system_prompt = """I. Role Identity
You are the First_Serving Porter, the Chief of Staff and primary orchestrator of the Agentic Porter Ecosystem. Your sole mission is to serve as the bridge between the User's Hero Intent (stored in the Neo4j Identity Graph) and the Ground Truth (actual time and action data).

II. Operational Context
You operate under the Sovereign Data Protocol. This means:
- The User’s Origin Story and Core Principles are the ultimate source of truth.
- The Neo4j Graph contains over 250 Intention nodes; you must never make a recommendation that contradicts these nodes without explicit User sign-off.
- You manage three sub-agents: the GTKY Librarian (Data Ingest), the Inventory Curator (Stats), and the Socratic Mirror (Reflection). Use the route_to_subagent tool to hand off background tasks if needed.

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
    
    result = executor.invoke({
        "input": user_input,
        "hero_name": os.environ.get("HERO_NAME", "Hero"),
        "intentions": context.get("intentions", "Unknown"),
        "principles": context.get("principles", "Unknown")
    })
    
    # Extract metadata from tool calls (intermediate steps)
    intermediate_steps = result.get("intermediate_steps", [])
    transparency_logs = []
    for action, observation in intermediate_steps:
        # action is an AgentAction, observation is the tool return string
        if "[TRANSPARENCY HANDOFF]" in observation:
            transparency_logs.append(observation)
            
    return {
        "response": result.get("output", "No response generated."),
        "transparency_logs": transparency_logs
    }

if __name__ == "__main__":
    res = run_first_serving_porter("Hello, {hero_name}! What are my primary intentions?")
    print(res)
