# Mach 3 & Beyond Roadmap: The Agent Ecosystem

While Mach 2 established the rigid data pipelines and memory graph, **Mach 3** and future iterations represent the sprawling intelligence layer.

## Core Future Initiatives

### 1. Vector Database Migration
- [ ] **Scale Beyond ChromaDB:** As the document parsing and historical logs grow, eventually migrate from a local SQLite/Chroma instance to a fully managed, production-grade Vector Database (e.g., Pinecone, Weaviate, or Qdrant).

### 2. Expanded Ingestion Integrations
- [ ] **Trello Board Sync:** Ingesting project management artifacts.
- [ ] **Google Tasks:** Reading explicit to-do checklist completions.
- [ ] **Figma Tracking:** Integrating creative effort logging to broaden the scope of the Hero's footprint.

### 3. The Autonomous Crew (New Agents)
As defined in the `AGENT_REGISTRY.md`, build out the specialized agent network:
- [ ] **The First-Serving Porter:** The front-man manager that reads quotas and outputs 2-3 definitive daily recommendations for the user.
- [ ] **GTKY Expansion:** Providing the "Getting To Know You" agent direct write-access to project long-term milestone nodes directly onto the graph.
- [ ] **The Analyzer Porter:** Training a tiny regression/LLM model strictly to output hard "Hero Numbers" (calculating the mathematical delta between intent and reality).
- [ ] **Sergeant & Campaign Porters:** Implementing agents purely capable of breaking massive 5-year aims into tiny weekly quota tickets.
- [ ] **The Grand Visionary:** Exploring Reinforcement Learning (PPO) to predict burnout or success pathways based off complex graph node multi-hops.
