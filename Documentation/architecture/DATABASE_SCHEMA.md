# Database Schema: The Identity Graph

Unlike relational models, the Neo4j database uses a Graph architecture built to act as the user's "digital memory." Relationships are first-class citizens connecting goals across long periods of time. All interactions map the human transition from Intention (Blueprint) to Reality (Actual).

## Core Node Definitions

| Label | Description | Schema Properties |
| :---- | :---- | :---- |
| **`Hero`** | The sovereign identity of the porter user. Drives the entire ecosystem. | `name: String` |
| **`Artifacts`** | Feature Node containing long-term static identity, intents, and principles. | `name: String` |
| **`Journal`** | Feature Node containing daily reflections and chronologies. | `name: String` |
| **`Calendar`** | Feature Node containing scheduling streams. | `name: String` |
| **`Day`** | Chronological temporal anchor for all events linked to the Journal. | `date: String`, `weekday: String` |
| **`TimeChunk`** | A distinct segment of the day (e.g., Morning, Evening) | `id: String` |
| **`Intent`** | The desired plan or "Blueprint." Usually ingested from Ambitions or Goals. | `category: String`, `description: String` |
| **`Event`** | Ingested events from Google Calendar that map to Intents. | `title: String`, `start_iso: String`, `duration_min: Integer` |
| **`Actual`** | The "Ground Truth." What specifically occurred during the `TimeChunk`. | `activity: String`, `feeling: String`, `isValuableDetour: Boolean`, `brainFog: Integer` |
| **`Delta`** | The calculable gap between Intent and Actual (Phase B Logic). | `status: String` |

## 2. Google Calendar Payload Formatting (Twin-Track Ingestion)
The backend employs a "Twin-Track" data strategy. Raw streaming data from the Google Calendar API lands in MongoDB first as a staging zone. Before the data is merged into the Neo4j Identity Graph, it is heavily formatted by `calendar_parser.py` using the following heuristic logic:

1. **Timing Extraction:** `start.dateTime` and `end.dateTime` are parsed to calculate `duration_minutes`. The `TimeChunk` (e.g., "Early Morning", "Afternoon") is mathematically derived from the `start.dateTime` hour.
2. **Category Extraction (The Color Mapping):** The Google Event's `colorId` property is cross-referenced strictly against the user's localized `.auth/category_mapping.json` file. This securely maps arbitrary UI color tags to formal graph `Pillars` (e.g., "Professional-growth") and `Subcategories`.
3. **Intent vs Actual Derivation:** If an event's `updated` timestamp occurred *after* the `start.dateTime`, the system heuristically flags the payload as a logged `Actual`. If it was unmodified after the start, it remains an `Intention`.

This isolated extraction produces the finalized JSON payload that is permitted to trigger the `MERGE` into Neo4j `Event` and `Intent` nodes.

## 3. Relationship Map

The architecture bridges intention with lived reality via these edge relationships:

1. `(Hero)-[:HAS_ARTIFACTS]->(Artifacts)`: Stores static memory.
2. `(Hero)-[:HAS_JOURNAL]->(Journal)`: Stores fluid chronological memory.
3. `(Hero)-[:HAS_CALENDAR]->(Calendar)`: Stores schedule memory.
4. `(Journal)-[:HAS_DAY]->(Day)`: Connects the journal to the timeline.
5. `(Day)-[:HAS_CHUNK]->(TimeChunk)`: Every day is sliced into distinct manageable zones.
6. `(TimeChunk)-[:RECORDED]->(Actual)`: The reality that was logged for that zone.
7. `(Actual)-[:PRODUCED]->(Delta)`: Connects a ground truth reality to a productivity calculation gap.
8. `(Calendar)-[:HAS_EVENT]->(Event)`: Extracted Calendar Event blocks.
9. `(Event)-[:FULFILLS]->(Intent)`: Bridge linking schedule to ambition.

### Idempotency Strategy
The system utilizes pure `MERGE` patterns for nodes like `Day` and `User` to ensure that duplicate synchronizations with Google Calendar API streams do not bloat the database. Over 250 intention nodes currently exist in this structured state.
