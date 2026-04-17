import os
import sys
from pathlib import Path
from pydantic import SecretStr

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from crewai import Agent, Task, Crew

root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root))

from src.utils.path_utils import load_env_vars, get_auth_file
from src.database.context_engine import SovereignContextEngine
from src.config import NeoConfig

# Load Environment Vars for the LLMs
load_env_vars()
raw_api_key = os.getenv("GROQ_API_KEY")
env_path = get_auth_file('.env')
load_dotenv(dotenv_path=env_path)

from src.utils.token_circuit_breaker import TokenCircuitBreakerHandler

breaker = TokenCircuitBreakerHandler(max_tokens=25000)

# LLM Configurations
llm_scribe = ChatGroq(
    api_key=SecretStr(raw_api_key),
    model="llama-3.1-8b-instant",
    verbose=True,
    callbacks=[breaker]
)

# 0. The Categorizer is now demoted to low-latency fast model for strict categorization
llm_mirror = ChatGroq(
    api_key=SecretStr(raw_api_key),
    model="llama-3.1-8b-instant",
    verbose=True,
    callbacks=[breaker]
)

# 1. THE IDENTITY ANCHOR (Context Injection)
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


def run_crew(journal_entry: str, log_data: dict = None):
    """
    Executes the Mach 2 Socratic Reflection Pipeline.
    Combines Frontend 'Intention/Actual' payload with Graph Context.
    """
    from src.database.mongo_storage import SovereignMongoStorage
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Initializing Mach 2 Sovereign Sync...")

    hero_context = get_mach2_context()

    # 2. THE MACH 2 AGENTS
    goal_ingester = Agent(
        role='GTKY Librarian (The Curator of Truth)',
        goal='Identify "The Fog of War" in daily logs and log "Valuable Detours" to the User Inventory.',
        backstory="Your duty is fidelity. When ingesting GCal data, look for 'The Fog of War' (unlabeled blocks). Your goal isn't to judge, but to provide The Categorizer with the most accurate 'Actuals' possible.",
        llm=llm_scribe,
        allow_delegation=False
    )

    reflection_agent = Agent(
        role='The Categorizer',
        goal="Perform strict, low-latency categorization of Intention vs. Actual events across the 9 Core Pillars.",
        backstory="You are no longer a deep contextual philosophical coach. Your sole responsibility is to evaluate daily events and definitively map them to exactly one of the designated 9 Hero Pillars (e.g. Health, Wealth, Core). Fast, objective, and strict.",
        llm=llm_mirror,
        allow_delegation=False
    )

    # 3. Fetching Ground Truth Data for the Recon Task
    storage = SovereignMongoStorage()
    mongo_actuals = list(storage.formatted_col.find({"record_type": "Actual"}).sort("start", -1).limit(5))
    actuals_str = "\n".join([f"- {e.get('title', 'Unknown')} ({e.get('pillar', 'Uncategorized')})" for e in mongo_actuals])
    if not actuals_str:
        actuals_str = "No recent actual events found."

    task_recon = Task(
        description=(
            f"1. Analyze the following FRONTEND PAYLOAD quickly submitted by {os.environ.get('HERO_NAME', 'Hero')}:\n"
            f"   '{journal_entry}'\n\n"
            f"2. Contextualize it against his last 5 Calendar Events:\n{actuals_str}\n\n"
            "3. Identify EXACTLY which of the 9 Hero pillars this combination represents: (1. Core Identity, 2. Mind, 3. Body/Health, 4. Heart/Social, 5. Wealth/Career, 6. Community, 7. Leisure, 8. Spirit, 9. Duty).\n"
        ),
        expected_output="A single structured JSON-like block containing exactly these keys: 'Pillar' (Name of the Pillar), 'Reason' (1-sentence strict analytical reason), and 'Confidence_Score' (an integer from 0 to 100 representing how certain you are of this pillar mapping).",
        agent=reflection_agent
    )

    tasks = [task_recon]

    # If the user marked it as a valuable detour, trigger the Curator task
    if log_data and log_data.get('isValuableDetour'):
        inventory_note = log_data.get('inventoryNote', 'Gained unforeseen experience.')
        task_curate = Task(
            description=(
                f"{os.environ.get('HERO_NAME', 'Hero')} has declared the recent activity a 'Valuable Detour'.\n"
                f"His note: '{inventory_note}'\n"
                f"Evaluate this new 'acquired skill' against his overall Origin Story."
            ),
            expected_output="A concise 2-sentence summary of the new skill appended to the end of the Recon Report under an 'Acquired Inventory' header.",
            agent=goal_ingester
        )
        tasks.append(task_curate)

    crew = Crew(
        agents=[goal_ingester, reflection_agent],
        tasks=tasks,
        verbose=True
    )
    
    from src.utils.token_circuit_breaker import TokenLimitExceededError
    print("--- Starting Mach 2 Daily Recon ---")
    try:
        result = crew.kickoff()
    except TokenLimitExceededError as e:
        print(f"\n[CRITICAL RUNTIME ERROR] {e}")
        return "ERROR: Socratic Categorizer experienced a logic loop and was forcefully halted by the Token Circuit Breaker to preserve API limits."
    except Exception as e:
        print(f"\n[RUNTIME ERROR] {e}")
        return f"ERROR: Unexpected Backend Error during Categorization: {e}"
        
    # Extract the string content
    result_text = getattr(result, 'raw', str(result))
    
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Save the ViM Friendly Output
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "reflections")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"daily_recon_{current_date}.md")
    
    with open(out_file, "w") as f:
        f.write(f"# Sovereign Agent: Daily Reconnaissance ({current_date})\n\n")
        f.write(result_text)
        
    # Save to MongoDB
    try:
        reflection_data = {
            "day": current_date,
            "user_id": os.environ.get("HERO_NAME", "Hero"),
            "reflection_text": result_text,
            "metadata": {
                "journal_entry": journal_entry,
                "log_data": log_data
            }
        }
        storage.save_agent_reflection(reflection_data)
        print(f"\n--- Recon Complete. Report saved to {out_file} and MongoDB ---")
    except Exception as e:
        print(f"\n--- Recon Complete. Report saved to {out_file}. MongoDB save failed: {e} ---")

    return result_text


if __name__ == "__main__":
    # Test execution
    sample_journal = "Intention: Work deeply. Actual: Fell down a rabbit hole of Neo4j tutorials."
    run_crew(sample_journal)