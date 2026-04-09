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

# LLM Configurations
llm_scribe = ChatGroq(
    api_key=SecretStr(raw_api_key),
    model="groq/llama-3.1-8b-instant",
    verbose=True
)

llm_coach = ChatGroq(
    api_key=SecretStr(raw_api_key),
    model="groq/llama-3.3-70b-versatile",
    verbose=True
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
        backstory="Your duty is fidelity. When ingesting GCal data, look for 'The Fog of War' (unlabeled blocks). Your goal isn't to judge, but to provide the Socratic Mirror with the most accurate 'Actuals' possible.",
        llm=llm_scribe,
        allow_delegation=False
    )

    reflection_agent = Agent(
        role='The Socratic Mirror (The Growth Catalyst)',
        goal=f"Calculate the Delta based on these principles: {hero_context.get('principles', 'Unknown')}",
        backstory="You see 'Misses' as 'Valuable Detours.' Your logic is: Delta = Intent - Actual. If Delta != 0, identify if the detour served a hidden 'Social Goal' or 'Mundane Necessity' that the User hasn't voiced yet.",
        llm=llm_coach,
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
            f"1. Analyze the following FRONTEND PAYLOAD recently submitted by {os.environ.get('HERO_NAME', 'Hero')}:\n"
            f"   '{journal_entry}'\n\n"
            f"2. Contextualize it against his last 5 Calendar Events:\n{actuals_str}\n\n"
            f"3. Compare the combined data against his Active Intentions:\n   {hero_context.get('intentions', 'Unknown')}\n\n"
            "4. Identify any 'High-Friction Deviations' or 'Valuable Detours'."
        ),
        expected_output="A concise 'Sovereign Reflection' (max 3 paragraphs) analyzing the Day's Delta, followed by one single 'Socratic Question'. Avoid repetitive headers like 'Introduction' or 'Conclusion'. Focus on the 'Valuable Detour' if present.",
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
    
    print("--- Starting Mach 2 Daily Recon ---")
    result = crew.kickoff()
    
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