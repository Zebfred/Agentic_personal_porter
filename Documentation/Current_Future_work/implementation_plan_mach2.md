# Mach 2 Completion, Future Roadmap, & Security Patch

This plan outlines the next phase of development for the Agentic Personal Porter, addressing your questions about the state of Mach 2, outlining the roadmap based on your TO-DO list, and providing an immediate security fix for the public repo.

## 1. State of the Union: Formal Mach 2 Completion Checklist
**Answer: No, we are not truly done with Mach 2.** 
The following technical hurdles must be cleared to formalize Mach 2's completion:

- [ ] **Achieve Consistent Idempotency**: The `MERGE` logic must be rigorously tested against the full historical JSON samples to ensure that repeated syncs do not degrade graph performance or create "ghost" relationships.
- [ ] **Finalize the "Daily Recon" UI**: The frontend must prioritize the 20-second verification loop, ensuring that agent-inferred labels are easy to correct or confirm with minimal cognitive load.
- [ ] **Expand the Socratic Reflection Prompts**: The "Fog of War" detection logic should be refined to distinguish between "Restorative Rest" (which is a win in Maslow's hierarchy) and "Mindless Stagnation" (which is an undesirable future).
- [ ] **Establish a Robust Backup Strategy**: Secure the `.auth` directory and neo4j exports.

## 2. Immediate Security Patch (Critical)
You correctly identified that `src/constants.py` exposes deeply personal PII (e.g., family references, specific tasks like "jury duty", specific habits). Since this is a public repository, this is a glaring security hole.

### Proposed Fix:
1. **Extract Data:** Move the `ACTUAL_CATEGORY_MAPPING` out of `src/constants.py` and into a git-ignored JSON file located at `.auth/category_mapping.json`.
2. **Update Constants:** Refactor `src/constants.py` to use `json.load()` to read from this protected file dynamically.
3. **Provide Template:** Create a `data/category_mapping.example.json` with highly generic placeholder data so other developers cloning the repo can still run the app without seeing your specific goals.

## 3. Immediate Documentation Updates
- Update `Documentation/architecture/DATABASE_SCHEMA.md` to include a section detailing exactly how the Google Calendar JSON payloads are formatted and translated into the `Intention` and `TimeChunk` nodes.

## 4. Short-Term Roadmap (Completing Mach 2)
To cross the finish line for Mach 2, we will tackle the following tasks in upcoming development iterations:
1. **Neo4j Refactoring:** Break down `neo4j_db.py` into an inheritable database class architecture, ensuring the connection logic perfectly matches the expected graph model.
2. **Robust GCal Pipeline:** Implement daily pulls from Google Calendar to initially land in **MongoDB** for formatting and time-series storage, before eventually merging the formatted data into Neo4j.
3. **Hero Foundation Frontend:** Rework `inject_hero_foundation` to pull directly from new UI components on the frontend, saving the artifacts properly to storage.

## 5. Long-Term Roadmap (Mach 3 & Beyond)
Based on your `Mar_Brainstorming.md` and integration notes, future development will encompass:
- **Expanded Integrations:** Trello, Google Tasks, and Figma integrations for a wider data-net encompassing the Hero's footprint.
- **The First-Serving Porter:** A front-man "manager" agent that presents 2-3 weighted options to the user for daily action.
- **The GTKY Upgrades:** Giving the GTKY agent the power to project long-term milestones and calculate hard numerical differences between intent and actual.
- **The Analyzer Porter:** Utilizing regression or small LLMs to calculate the "Hero Numbers" representing forward progress, neutrality, or backstepping.
- **Vector DB Migration:** Evolving past ChromaDB to a proper production Vector Database (e.g., Pinecone/Weaviate) when scaling requires it.

## User Review Required
Does this accurately capture your vision for the remaining development steps? If you approve, I will immediately execute **Section 2 (Security Patch)** and **Section 3 (Documentation Updates)** right now to plug the hole and close the documentation gap.
