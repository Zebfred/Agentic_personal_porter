# MongoDB & Neo4j Hybrid Graph Architecture

## Overview
This document formalizes the new "Polyglot Persistence" architecture for Agentic Personal Porter. The system utilizes MongoDB as the dynamic "Source of Truth" for keyword classification and raw data storage, while Neo4j serves as the rigid relationship map tying intents and actual events to the Hero's chronological timeline and core pillars.

## 1. Neo4j Graph Structure
The graph models the Hero's identity, temporal structure, and execution of intents.

### Center Node
- `(Hero {id: userid})`

### Primary Branches
- `(Hero)-[:DIRECTED_BY]->(Artifacts: Origin, Principles, Ambition)`
- `(Hero)-[:ADHERES_TO]->(Pillars)`
- `(Hero)-[:ADHERES_TO]->(Time)`

### Temporal Structure (Dynamic Generation)
Time nodes are generated on-demand when a Calendar Event or Journal Entry falls into them.
- `(Time)-[:HAS_WEEK]->(Week)-[:HAS_DAY]->(Day)-[:HAS_TIME_CHUNK]->(TimeChunk)`
- **TimeChunk**: 4-hour blocks (6 per day). E.g., `2024-W18-D1-C3`.

### Execution (Intent vs. Actual)
- **Intent**: Calendar Events. `(TimeChunk)-[:PLANNED_AS]->(Intent)`
- **Actual**: Journal Entries / Confirmed Events. `(TimeChunk)-[:RECORDED_AS]->(Actual)`
- **Classification**: Both Intent and Actual bridge to Pillars: `(Intent)-[:CLASSIFIED_AS]->(Pillars)`
- **Evaluation Bridges**:
  - `(Intent)-[:MATCH]->(Actual)`
  - `(Intent)-[:NOT_MATCH]->(Detour)` -> `Valuable Detour` or `Detrimental Detour`

*(Note: The "One-Way Valve" rule enforces that Intent and Actual nodes MUST be children of a TimeChunk, preventing floating events).*

## 2. MongoDB Schema (The Classification Engine)
MongoDB acts as the classification dictionary and raw data store to keep Neo4j lean.

### A. `PillarClassifications` Collection
Acts as the ground truth for AI agents mapping keywords to Life Pillars before creating `:CLASSIFIED_AS` relationships in Neo4j.
```json
{
  "_id": "ObjectId",
  "pillar_name": "Health", 
  "keywords": [
    {"term": "gym", "confidence": 1.0, "source": "manual"},
    {"term": "meal prep", "confidence": 0.85, "source": "ai_suggested"}
  ],
  "last_updated": "2024-04-29T14:00:00Z",
  "neo4j_node_id": "p_health_01" 
}
```

### B. `ConfirmedActuals` Collection
Stores the full JSON of human-confirmed actual events.
```json
{
  "_id": "ObjectId",
  "time_chunk_id": "2024-W18-D1-C3",
  "raw_input": "Finished the heavy lifting session.",
  "extracted_keywords": ["lifting", "gym"],
  "assigned_pillars": ["Health"],
  "human_confirmed": true,
  "metadata": {
    "is_valuable_detour": false,
    "matches_intent": true
  }
}
```

## 3. The Sync Loop
1. **AI Detection:** Agent receives journal input, queries `PillarClassifications` in MongoDB to match keywords.
2. **Graph Update:** Agent creates `(:Actual)` node in Neo4j, drawing `:RECORDED_AS` from the dynamic `(:TimeChunk)`.
3. **Human Feedback:** User overrides/confirms tags. Agent updates `PillarClassifications` in MongoDB and adjusts `:CLASSIFIED_AS` edges in Neo4j.

## Future Improvement
- **Neo4j APOC:** Explore using Neo4j APOC to query MongoDB directly within Cypher for real-time validation, bypassing the Python orchestrator. (Currently acceptable to use Python Orchestrator with standard Cypher).
