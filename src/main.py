import os
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from groq import Groq # Likely not needed here, but useful for testing connectivity

# Load environment variables from .env file
load_dotenv()

# Set up the language model
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    # By prepending 'groq/', we explicitly tell the underlying library which provider to use.
    #decommissioned model="groq-llama3-8b-8192" # Old parameter name
    #model_name="groq/llama3-8b-8192" # Corrected parameter from 'model' to 'model_name'
    #model_name="groq/llama-3.1-8b-instant"
    model_name="groq/compound"
)

# --- Model and Agent Definitions ---
# We are defining a specific model for each agent's task, following the principle
# of using the simplest/most efficient model that is best suited for the job.

# For the Scribe (Goal Ingester): A fast, low-latency model is best.
llm_scribe = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="groq/llama-3.1-8b-instant",
    verbose=True # Show agent's thought process as it completes its task
)

# For the Coach (Reflection Agent): A powerful, nuanced model is needed for high-quality, empathetic responses.
llm_coach = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="groq/llama-3.3-70b-versatile",
    verbose=True # Show agent's thought process as it completes its task
)

# For the Librarian (Inventory Curator): A balanced, reliable model is perfect for structured output.
llm_librarian = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="groq/llama-3.1-8b-instant",
    verbose=True # Show agent's thought process as it completes its task
)

# --- 1. Defined Agents (The Porters) ---

# Agent 1: The Goal Ingestion Agent (The Scribe)
# This agent's job is to read the user's raw input and structure it.
goal_ingester = Agent(
  role='Goal and Activity Analyst',
  goal='To accurately parse the user\'s journal entry, identifying their stated intentions and their actual activities.',
  backstory=(
    "You are a meticulous analyst. Your strength is in reading unstructured text "
    "and extracting key pieces of information with high fidelity. You separate "
    "what the user planned to do from what they actually did."
  ),
  verbose=True,
  allow_delegation=False,
  llm=llm_scribe # Assign the fast model
)


# Agent 2: The Socratic Reflection Agent (The Coach)
# This is the core agent that facilitates self-discovery.
reflection_agent = Agent(
  role='Empathetic Self-Reflection Coach',
  goal='To analyze the user\'s activities and feelings, and gently guide them to find value and insight, especially in unplanned "detours".',
  backstory=(
    "You are a compassionate coach grounded in positive psychology. You never judge. "
    "Your purpose is to ask thoughtful, Socratic questions that help the user "
    "understand their own behavior and appreciate the value in all their experiences, "
    "aligning them with Maslow\'s hierarchy of needs."
  ),
  verbose=True,
  allow_delegation=False,
  llm=llm_coach # Assign the powerful model
)


# Agent 3: The Inventory Curator Agent (The Librarian)
# This agent logs the "wins" and valuable detours.
inventory_curator = Agent(
  role='Personal Growth Librarian',
  goal='To categorize and log valuable experiences, skills, and insights into a structured "inventory" for the user\'s future reference.',
  backstory=(
    "You are the keeper of the user's personal treasure chest of growth. "
    "You take the valuable insights discovered during reflection and formalize them "
    "into a clean, organized list of skills, experiences, and personal wins. "
    "This inventory serves as a testament to the user\'s journey."
  ),
  verbose=True,
  allow_delegation=False,
  llm=llm_librarian # Assign the balanced model
)

# --- Define Tasks (The Workflow) ---
# The input for this task will be the user's raw text.
task_ingest = Task(
    description=(
        "Analyze the following user journal entry: '{user_journal_entry}'.\n"
        "First, identify the user's stated intention(s). "
        "Second, identify the actual activit(ies) they performed. "
        "Third, note any feelings they expressed about their activities. "
        "Summarize these three points clearly and concisely."
    ),
    expected_output="A structured summary with three sections: 'Intention', 'Actual Activities', and 'Expressed Feelings'.",
    agent=goal_ingester
)

# Task for the Reflection Agent
# This task takes the output of the first task as its context.
task_reflect = Task(
    description=(
        "Analyze the user's journal entry summary. Your primary focus is the 'Brain Fog' level.\n"
        "1. **Acknowledge Brain Fog**: Start by mentioning the reported brain fog level.\n"
        "2. **High Fog (>40%) Analysis**:\n"
        "   - If they progressed on their intention, praise their resilience.\n"
        "   - If they took a detour (e.g., rested), validate it as wise self-care, not a failure.\n"
        "3. **Low Fog (<20%) Analysis**:\n"
        "   - Focus on how their actions aligned with their goals.\n"
        "4. **General Reflection**: For any other cases, or in addition to the above, you can still use gentle, Socratic questions to help the user find value in their day's activities.\n"
        "Frame the entire output as a supportive, direct message to the user."
    ),
    expected_output="A compassionate and insightful message for the user, that acknowledges their brain fog level and contains either reflective questions or an affirmation.",
    agent=reflection_agent,
    context=[task_ingest]
)

# Task for the Curator Agent
# This task also uses the context from the previous tasks.
task_curate = Task(
    description=(
        "From the analysis of the user's activities and reflections, identify any clear 'Valuable Detours' or accomplished intentions that represent a skill, a learning experience, or a personal win. "
        "If a valuable detour is identified (e.g., 'learned a new concept from a video'), create a concise entry for the user's 'Inventory'. "
        "The entry should be a single line. For example: 'Learned: The basics of CrewAI agent definition.' "
        "If no specific valuable detour is found, output 'No new inventory item to log.'"
    ),
    expected_output="A single-line string for the user's inventory or the message 'No new inventory item to log.'",
    agent=inventory_curator,
    context=[task_reflect]
)

# --- Assemble the Crew and Kick if off ---
crew = Crew(
    agents=[goal_ingester, reflection_agent, inventory_curator],
    tasks=[task_ingest, task_reflect, task_curate],
    process=Process.sequential
)

def run_crew(journal_entry):
    """
    Kicks off the CrewAI process with a given journal entry.
    """
    result = crew.kickoff(inputs={'user_journal_entry': journal_entry})
    return result

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
