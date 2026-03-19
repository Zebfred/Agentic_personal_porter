# Agent Registry

The Porter's core AI intelligence relies on the CrewAI framework powered by the Groq API. Below is the registry defining the active "Crew" that processes user journals into structured Neo4j data.

## 1. Goal Ingestion Agent
- **Alias:** The Logistics Coordinator
- **Role:** Extracts the "noise" or messy shorthand from the user's Google Calendar and Journal strings, parsing it into a strict, structured graph pattern.
- **Objective:** To separate Intentions from Actuals.
- **Expected Output:** Cleanly categorized strings separating the *Blueprint* from the *Reality* without missing subtle context.

## 2. Socratic Reflection Agent
- **Alias:** The Non-Judgmental Companion 
- **Role:** Calculates the "Delta" between human intention and realized action.
- **Objective:** Generates the empathetic response shown on the front-end to the user.
- **Guidelines:** The tone must be supportive, professional, and slightly witty. They act like a good butler ("Sir..."). If they notice "The Fog of War" (unaccounted time), they do not scold; they gently ask if it was a necessary detour for rest or a distraction. 

## 3. Inventory Curator Agent
- **Alias:** The Quartermaster (or GTKY Librarian)
- **Role:** Analyzes the `Actual` tasks to discover newly earned "XP", skills, or insights and logs them into long-term tracking nodes.
- **Objective:** Automatically categorizes tasks into life pillars (Professional-growth, Relationship-depth) and adds positive "Valuable Detours" into the Hero's Inventory.
- **Expected Output:** Emits the metadata bound for `(Achievement)` nodes.

---

### Upcoming Architectures (Mach 2 & 3)

1. **Reinforcement Learning "Life Guide" (Proposed):** An agent designed specifically to forecast "burnout" or "success" by processing multi-hop paths in the Neo4j graph using Proximal Policy Optimization (PPO).
2. **GTKY Brain Agent:** Expanding the Inventory Curator to actively synthesize the user's "Origin Story" (childhood/military history) against their mapped "Future Ambitions" (e.g. moving to Fiji).
