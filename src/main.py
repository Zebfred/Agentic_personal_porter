import os
from src.agents.crew_manager import run_crew
from src.utils.path_utils import load_env_vars

# Load environment variables from .env file
load_env_vars()

# --- Main execution block ---
if __name__ == "__main__":
    print("--- Running CrewAI Standalone Test ---")
    sample_journal_entry = (
        "Today is Sunday. My intention was to jump right into coding the CrewAI implementation for my project. "
        "Instead, I spent about 2 hours just resting and another 45 minutes looking at the code and planning, feeling some resistance before finally starting. "
        "I feel good that I eventually got started and made progress."
    )

    # Kick off the crew's work!
    final_result = run_crew(sample_journal_entry)

    print("\n\n--- CrewAI Workflow Complete ---")
    print("Final Result:")
    print(final_result)
