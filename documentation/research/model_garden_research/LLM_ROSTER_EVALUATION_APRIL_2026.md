# LLM Roster Evaluation & Sovereign Architecture Review (April 2026)

**Role:** Paul, Senior Principal Engineer and LLM/RAG Architect. 
**Objective:** Evaluate Agent-to-LLM mappings. We must defend our sovereign architecture while leveraging April 2026 model advancements.
**Core Constraint:** Every recommendation must serve the **< 20-second human friction rule** and optimize our core engine: calculating $\Delta = \text{Actual} - \text{Intention}$ or The Agentic Workflow Architecture of a Managing agent for a crew of other agents. 

---

## 1. Reality Audit: Notebook Assumptions vs. Production Reality

An automated audit of the `src/agents/` directory reveals several discrepancies between our high-level design notes and the active codebase.

| Agent / Component | Notebook Assumption | Production Reality (Audit April 18) | Status |
| :--- | :--- | :--- | :--- |
| **First-Serving Porter** | `groq/compound` | `llama-3.3-70b-versatile` | **Discrepancy** |
| **The Categorizer** | `llama-3.3-70b-versatile` | `llama-3.1-8b-instant` | **Demoted (Speed Focus)** |
| **GTKY Librarian** | `gemma2-9b-it` | `llama3-70b-8192` | **Upgraded (Accuracy Focus)** |
| **Time Keeper** | `llama-3.1-8b-instant` | `llama-3.1-8b-instant` | **Match** |
| **Embeddings** | Local `BGE-M3` | Split: `BGE-M3` + `OpenAI text-3-small` | **Fragmented** |

---

## 2. The "OpenAI Deprecation" Directive
> [!CAUTION]
> **Strategic Pivot:** Due to market turbulence and non-sovereign standing, **OpenAI (GPT/Embeddings) is hereby demoted.** ALL active components using `text-embedding-3-small` dependencies or similar GPT models will be used only after careful consideration and approval for that specific use case. Future cloud fail-safes are strictly limited to **Groq**, **Google (Gemini)**, or **Anthropic (Claude)**.

---

## 3. Finalized Mach 3.5 Verdicts & Upgrades

### A. Socratic Mirror (Logic-Heavy Delta Analysis)
*   **Verdict:** Promote to **DeepSeek-R1**.
*   **Rationale:** The "demotion" to Llama 3.1 8B in March sacrificed the reasoning required for deep "Delta" analysis. `DeepSeek-R1`'s GRPO-trained Chain-of-Thought reasoning is the optimal "Reasoning Provider" to understand why intentions failed to match actuals.
*   **Implementation:** Use `DeepSeek-R1` strictly for the "Reason" and "Pillar" mapping to ensure logic fidelity.

### B. The First-Serving Porter (Lead Orchestrator)
*   **Verdict:** Adopt **Gemma 4 (26B MoE)** for local edge performance.
*   **Rationale:** Benchmarks show 85 tokens/sec on consumer hardware. This provides GPT-4 level orchestration at near-zero latency, maintaining total local sovereignty. 
*   **Cloud Fail-safe:** Claude 3.5 Sonnet.

### C. The Time_Keeper & Goal Ingestion (Batch Parsing)
*   **Verdict:** Transition to **Qwen 3.5 9B**.
*   **Rationale:** Superior logic-per-watt and cost efficiency ($0.10/M tokens). Ideal for heavy cron jobs parsing GCal JSON arrays into Mongo Time-Series.

### D. The GTKY Librarian (Full Context Knowledge)
*   **Verdict:** Adopt **Llama 4 Scout**.
*   **Rationale:** The 10 Million token context window allows the Librarian to "digest" the entire Neo4j Identity Graph and months of historical data in a single audit pass, eliminating RAG retrieval noise for identity verification.

---

## 4. Embedding Infrastructure Standardization
*   **Mandate:** **Standardize on Local `BGE-M3`.**
*   **Cleanup:** Purge `intuitive_memory_query.py` of OpenAI references. All matrix outputs remain local to the GCE-hosted endpoint to keep the reasoning budget focused on high-logic agents.
*   **Telemetry:** Do NOT trace embedding matrix outputs through LangSmith. Tracing is reserved for generative LLM calls.

---

## 5. Summary Table: Mach 3.5 Architecture

| Role | Final Model Selection | Tier | Priority |
| :--- | :--- | :--- | :--- |
| **First-Serving Porter** | **Gemma 4 (26B MoE)** | Orchestration | Speed/Sovereignty |
| **Socratic Mirror** | **DeepSeek-R1** | Reasoning | Logic/Delta |
| **GTKY Librarian** | **Llama 4 Scout** | Contextual | Memory/Audit |
| **Time_Keeper** | **Qwen 3.5 9B** | Utility | Efficiency |
| **Vibe Embedding** | **BGE-M3 (Local)** | Foundation | Sovereign |