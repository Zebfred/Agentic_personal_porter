# Neo4j Query Patterns

This document provides a robust reference for querying the Mach 2 Identity Graph. These queries use dynamic matching (omitting hardcoded Hero names) so they work seamlessly regardless of the `HERO_NAME` environment variable.

## 1. Top-Level Ecosystem Verification

**Are all Major Feature Nodes Connected?**
This query verifies that the central `Hero` node is successfully bridging out to the three critical pillars: `Artifacts`, `Journal`, and `Calendar`.

```cypher
MATCH (h:Hero)
OPTIONAL MATCH (h)-[r1:HAS_ARTIFACTS]->(art:Artifacts)
OPTIONAL MATCH (h)-[r2:HAS_JOURNAL]->(j:Journal)
OPTIONAL MATCH (h)-[r3:HAS_CALENDAR]->(c:Calendar)
RETURN h, r1, art, r2, j, r3, c
```

---

## 2. The Artifacts Feature Node (Long-Term Memory)

**Artifacts Graph (Visual):**
Expand the complete tree of Principles, Intents, Origins, and Epochs stemming from the Artifacts node.
```cypher
MATCH path = (h:Hero)-[:HAS_ARTIFACTS]->(art:Artifacts)-[*1..2]->(leaf)
RETURN path
```

**Artifacts Breakdown (Table):**
Tabulate the dense data held within the artifacts tree for easy reading.
```cypher
MATCH (h:Hero)-[:HAS_ARTIFACTS]->(art:Artifacts)-[r]->(leaf)
RETURN type(r) AS Relationship, labels(leaf)[0] AS NodeType, coalesce(leaf.name, leaf.category, "N/A") AS Primary_Label, leaf.description AS Description, leaf.text AS Text
ORDER BY NodeType
```

---

## 3. The Journal Feature Node (Daily Ground Truth)

**Journal Lineage (Visual):**
Visualizes the linear timeline extending from the Journal through Days, TimeChunks, Actuals, and Deltas.
```cypher
MATCH path = (h:Hero)-[:HAS_JOURNAL]->(j:Journal)-[:HAS_DAY]->(d:Day)-[:HAS_CHUNK]->(tc:TimeChunk)-[:RECORDED]->(a:Actual)
// Optionally extend to: -[:PRODUCED]->(delta:Delta)
RETURN path
```

**Journal Extract (Table):**
Generates a clean dashboard-ready table of all logged activities and corresponding feelings.
```cypher
MATCH (h:Hero)-[:HAS_JOURNAL]->(j:Journal)-[:HAS_DAY]->(d:Day)-[:HAS_CHUNK]->(tc:TimeChunk)-[:RECORDED]->(a:Actual)
RETURN d.date AS Date, tc.id AS TimeChunk, a.activity AS Activity, a.feeling AS Feeling, a.brainFog as BrainFog
ORDER BY Date DESC
```

---

## 4. The Calendar Feature Node (Planned Scheduling)

**Event Pathway (Visual):**
Visualize the Calendar schema bridging downloaded Events to the Hero's broader Life Intents.
```cypher
MATCH path = (h:Hero)-[:HAS_CALENDAR]->(c:Calendar)-[:HAS_EVENT]->(e:Event)-[:FULFILLS]->(i:Intent)
RETURN path
LIMIT 50
```

**Calendar Diagnostics (Table):**
Table showing orphaned events or raw Google Calendar pulls that haven't been successfully tied to an Intent yet.
```cypher
MATCH (h:Hero)-[:HAS_CALENDAR]->(c:Calendar)-[:HAS_EVENT]->(e:Event)
OPTIONAL MATCH (e)-[:FULFILLS]->(i:Intent)
RETURN e.title AS Event, e.start_iso AS Date, e.pillar AS Extracted_Pillar, coalesce(i.category, "ORPHANED") AS fulfillment_target
ORDER BY Date DESC
```
