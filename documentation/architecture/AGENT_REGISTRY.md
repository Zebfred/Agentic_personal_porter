# Agent Registry

The Porter's core AI intelligence relies on a **Dual System Architecture** powered by the Groq API (via LangChain primitives). We use:
- **CrewAI**: For batch-processing, multi-agent reflection (e.g., end-of-day Socratic Mirror analysis).
- **LangChain Tool-Calling Agents**: For instantaneous, low-latency, direct user-chat interactions on the Hub frontend.

Below is the registry defining the active agents.

## 1. Goal Ingestion Agent
- **Alias:** The Logistics Coordinator
- **Connection:** MongoDB (Reads Raw Logs), Neo4j (Writes Intentions via `calendar_parser.py`)
- **Role:** Extracts the "noise" or messy shorthand from the user's Google Calendar and Journal strings, parsing it into a strict, structured graph pattern.
- **Objective:** To separate Intentions from Actuals.
- **Expected Output:** Cleanly categorized strings separating the *Blueprint* from the *Reality* without missing subtle context.

## 2. Socratic Reflection Agent
- **Alias:** The Non-Judgmental Companion 
- **Connection:** Neo4j (Identity Graph Context), ChromaDB (Vectorized past reflections)
- **Role:** Calculates the "Delta" between human intention and realized action (Currently operational via CrewAI).
- **Objective:** Generates the empathetic response shown on the front-end to the user.
- **Guidelines:** The tone must be supportive, professional, and slightly witty. They act like a good butler ("Sir..."). If they notice "The Fog of War" (unaccounted time), they do not scold; they gently ask if it was a necessary detour for rest or a distraction. 

## 3. Inventory Curator Agent
- **Alias:** The Quartermaster
- **Connection:** Neo4j (Writes Achievement Nodes)
- **Role:** Analyzes the `Actual` tasks to discover newly earned "XP", skills, or insights and logs them into long-term tracking nodes.
- **Objective:** Automatically categorizes tasks into life pillars (Professional-growth, Relationship-depth) and adds positive "Valuable Detours" into the Hero's Inventory.
- **Expected Output:** Emits the metadata bound for `(Achievement)` nodes.

## 4. First-Serving Porter
- **Alias:** The Front Man (Chief of Staff)
- **Framework:** LangChain Tool-Calling Agent
- **Connection:** Interacts natively with the Hub UI websocket and dispatches API requests to CrewAI backend processes.
- **Role:** The primary user-facing recommender and chat interface on the Hub.
- **Function:** Operates under the Sovereign Data Protocol. Bridges the User's Hero Intent (Neo4j) and Ground Truth. It triggers tools to update Artifacts (Origin Story/Ambitions) and emits `[TRANSPARENCY HANDOFF]` logs when it intends to route a complex background task to the CrewAI sub-agents.

---

## Upcoming Architectures (Mach 3 & Beyond)

The future scale of the Porter relies on a sprawling, highly specialized crew of distinct agents operating on the Identity Graph:

1. **GTKY Agent (Getting To Know You)** *(Needs to be built)*
   - **Role:** Curator of the Hero's Intent, Origin Story, and Calendar space.
   - **Function:** Fully processes past and future contexts to fill gaps between the Origin Story and Hero's Intent. Calculates and passes raw difference integers representing Actual vs Intent (the "Hero Numbers") downward to the Analyzer.
   - **Connection:** Requires deep integration with Weaviate (Journal search) and Neo4j (Artifact graphs) to find subtle contradictions.

2. **Analyzer_Porter (The Statistician)** *(Needs to be built)*
   - **Role:** Evaluator of micro/macro Intent matching utilizing localized RL/Regression Models.
   - **Function:** Converts GTKY's data into hard numerical scores (Forward Progress, Neutral, Backstepping). These hard scores fuel data-driven behavioral nudges.
3. **Analyzer_Porter (The Statistician)**
   - **Role:** Evaluator of micro/macro Intent matching.
   - **Function:** A localized LLM or regression model that converts GTKY's data into hard numerical scores (Forward Progress, Neutral, Backstepping). These hard scores fuel data-driven behavioral nudges.

3. **Sergeant_Porter (The Taskmaster)** *(Needs to be built)*
   - **Role:** Creator of "Hero Missions" (weekly/monthly).
   - **Function:** Formulates standard Hero quota objectives, dictating the sheer quantity of tasks that should be pursued for a given week.

4. **Campaign_Porter (The Strategist)** *(Needs to be built)*
   - **Role:** The milestone architect bridging Neo4j constraints to the Mongo Time-Series log.
   - **Function:** Translates massively long-term Hero Intents into granular, workable milestones.

5. **Grand Visionary Porter (The Oracle)** *(Needs to be built)*
   - **Role:** The distant-future projector.
   - **Function:** Responsible for mapping +3, 5, 10, and 20-year trajectories all the way to end-of-life goals. Functions initially as an extension of GTKY until reliable predictive analytics (via RL/PPO pathways) are fully stabilized.
      - **Connection:** Replaces raw prompts with dedicated Python Tool Calls to forecasting libraries (like Prophet/LSTM Models) analyzing the Mongo data.

6. **Corrector_Porter (The Auditor)** *(Needs to be built)*
   - **Role:** The internal safeguard.
   - **Function:** Specifically dedicated to reviewing, parsing, and fixing the hallucinatory mistakes or logic gaps committed by the other agents in the execution chain.
      - **Connection:** Queries ChromaDB for historical "Hallucination errors" to prevent the First-Serving agent from making repeated logic bugs in the execution chain.
