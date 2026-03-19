# Database Schema: The Identity Graph

Unlike relational models, the Neo4j database uses a Graph architecture built to act as the user's "digital memory." Relationships are first-class citizens connecting goals across long periods of time. All interactions map the human transition from Intention (Blueprint) to Reality (Actual).

## Core Node Definitions

| Label | Description | Schema Properties |
| :---- | :---- | :---- |
| **`User`** | The sovereign identity of the porter user. Hardcoded as "Jimmy/Sir" currently. | `name: String`, `sovereign_id: String` |
| **`Day`** | Chronological temporal anchor for all events. | `date: String`, `weekday: String` |
| **`TimeChunk`** | A distinct segment of the day (e.g., Morning, Evening) | `chunk_name: String` |
| **`Intention`** | The desired plan or "Blueprint." Usually ingested directly from Google Calendar blocks. | `title: String`, `pillar_id: String` |
| **`Actual`** | The "Ground Truth." What specifically occurred during the `TimeChunk`. | `activity: String`, `feeling: String`, `isValuableDetour: Boolean`, `brainFog: Integer` |
| **`Achievement`** | Extracted from "Valuable Detours." A durable skill or learning added to the Inventory. | `title: String`, `description: String` |
| **`State`** | Emotional or cognitive conditions (like burnout, fog of war, or happiness) affecting the day. | `type: String`, `value: String` |

## Relationship Map

The architecture bridges intention with lived reality via these edge relationships:

1. `(User)-[:LIVED]->(Day)`: Connects the user to the day in the timeline.
2. `(Day)-[:HAS_CHUNK]->(TimeChunk)`: Every day is sliced into distinct manageable zones.
3. `(TimeChunk)-[:INTENDED]->(Intention)`: The expectations for that zone.
4. `(TimeChunk)-[:EXPERIENCED]->(Actual)`: The reality that was logged for that zone.
5. `(Actual)-[:AFFECTED_BY]->(State)`: Correlates a specific task with an emotional state.
6. `(User)-[:HAS_ACHIEVEMENT]->(Achievement)`: Direct long-term storage of user growth.

### Idempotency Strategy
The system utilizes pure `MERGE` patterns for nodes like `Day` and `User` to ensure that duplicate synchronizations with Google Calendar API streams do not bloat the database. Over 250 intention nodes currently exist in this structured state.
