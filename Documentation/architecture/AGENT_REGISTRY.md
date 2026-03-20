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

## Upcoming Architectures (Mach 3 & Beyond)

The future scale of the Porter relies on a sprawling, highly specialized crew of distinct agents operating on the Identity Graph:

1. **First_Serving_Porter (The Front Man)**
   - **Role:** The crew manager of the rest of the ecosystem.
   - **Function:** Serves as the primary user-facing recommender. Aggregates Milestones, Intentions, Quotas, Reflections, and "Hero Numbers" to provide 2-3 weighted options for daily/weekly necessary action. Highly responsive to dynamic user input for rapid adjustments.

2. **GTKY Agent (Getting To Know You)**
   - **Role:** Curator of the Hero's Intent, Origin Story, and Calendar space.
   - **Function:** Fully processes past and future contexts to fill gaps between the Origin Story and Hero's Intent. Calculates and passes raw difference integers representing Actual vs Intent (the "Hero Numbers") downward to the Analyzer.

3. **Analyzer_Porter (The Statistician)**
   - **Role:** Evaluator of micro/macro Intent matching.
   - **Function:** A localized LLM or regression model that converts GTKY's data into hard numerical scores (Forward Progress, Neutral, Backstepping). These hard scores fuel data-driven behavioral nudges.

4. **Sergeant_Porter (The Taskmaster)**
   - **Role:** Creator of "Hero Missions" (weekly/monthly).
   - **Function:** Formulates standard Hero quota objectives, dictating the sheer quantity of tasks that should be pursued for a given week (adjustable via user oversight).

5. **Campaign_Porter (The Strategist)**
   - **Role:** The milestone architect.
   - **Function:** Translates massively long-term Hero Intents into granular, workable milestones (e.g., parsing a 5-year plan into quarterly and yearly actionable objectives).

6. **Grand Visionary Porter (The Oracle)**
   - **Role:** The distant-future projector.
   - **Function:** Responsible for mapping +3, 5, 10, and 20-year trajectories all the way to end-of-life goals. Functions initially as an extension of GTKY until reliable predictive analytics (via RL/PPO pathways) are fully stabilized.

7. **Corrector_Porter (The Auditor)**
   - **Role:** The internal safeguard.
   - **Function:** Specifically dedicated to reviewing, parsing, and fixing the hallucinatory mistakes or logic gaps committed by the other agents in the execution chain.
