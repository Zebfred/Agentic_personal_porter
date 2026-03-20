# Neo4j Query Patterns

This document serves as a robust reference for querying the Identity Graph. These queries are essential for backend development, debugging, and fueling the analytical capabilities of advanced Mach 3 agents.

## 1. Core Graph Pathing

**The Complete Hero Trajectory:**
Visualizes the linear timeline extending from the root Hero node through their Origins, Epochs, and individual Experiences.

```cypher
MATCH path = (h:Hero {name: "Zeb"})-[:HAS_ORIGIN]->(o:Origin)-[:HAS_EPOCH]->(e:Epoch)-[:HAS_EXPERIENCE]->(x:Experience)
RETURN path
```

**Deep Exploratory Pathing:**
A powerful diagnostic query that explores relationships radially outward from the Hero node up to 3 hops deep. Perfect for discovering orphaned nodes or unexpected graph structures.

```cypher
MATCH path = (h:Hero {name: "Zeb"})-[*1..3]->(n)
RETURN path
```

## 2. Agent-Specific Targeting Pipelines

**The Mach 3 Agent Target List:**
Used by the GTKY or Socratic Coach to dynamically identify `Experience` nodes that have been ingested but still require human elaboration or AI classification.

```cypher
MATCH (e:Epoch)-[:HAS_EXPERIENCE]->(x:Experience)
WHERE x.status IN ['Candidate', 'Needs_Detail']
RETURN e.name AS Epoch, x.title AS Topic, x.status AS Status
ORDER BY e.timeframe
```

## 3. Behavioral Analysis (Intent vs. Actual)

The system calculates Delta ($\Delta = Actual - Intention$). When querying the unified calendar graph, you can isolate events based on these predefined classifications:

**Isolating Core Intentions:**
```cypher
MATCH (h:Hero {name: "Zeb"})-[:HAS_INTENTION]->(i:Intention)
// Optionally filter by timeframe or category
RETURN i.title as Title, i.expected_duration as Expected
```

**Isolating Reality (The Actuals):**
```cypher
MATCH (h:Hero {name: "Zeb"})-[:HAS_ACTUAL]->(a:Actual)
RETURN a.title as Title, a.logged_duration as Logged
```

*(Note: The integration layer maps Calendar color IDs to these labels: Colors `['1', '9', 'default']` map to Intentions, while colors `['2', '8', '10']` map to Actuals.)*

## 4. Calendar and Event Graphs

**Visualizing the Integration Pathway:**
Visualize the connection between your Hero, the Calendar ingestion node, and a sample of recorded Events.
```cypher
MATCH (h:Hero {name: 'Zeb'})-[:HAS_CALENDAR]->(c)-[r:HAS_EVENT]->(e:Event)
RETURN h, c, r, e
LIMIT 50;
```

**Visualizing Micro-to-Macro Fulfillment:**
Visualize how specific micro-Events formally fulfill your high-level Goals (`Intent` nodes).
```cypher
MATCH (e:Event)-[r:FULFILLS]->(i:Intent)
RETURN e, r, i
LIMIT 100;
```

## 5. Event Table Diagnostics

These queries generate tabular data excellent for dashboarding and analyzing event health or missing categorizations.

**Event Count by Record Type:**
```cypher
MATCH (e:Event)
RETURN e.record_type AS Type, count(e) AS Count
ORDER BY Count DESC;
```

**Intent vs. Pillar Mapping Analytics:**
```cypher
MATCH (h:Hero {name: 'Zeb'})-[:HAS_CALENDAR]->(c)-[:HAS_EVENT]->(e:Event)-[:FULFILLS]->(i:Intent)
RETURN i.category AS Intent_Node, e.pillar AS Event_Pillar, count(e) AS Total_Linked
ORDER BY Total_Linked DESC;
```

**Find Uncategorized Events (Triaging needs):**
```cypher
MATCH (e:Event {pillar: 'Uncategorized'})
RETURN e.title, e.start_iso, e.duration_min
ORDER BY e.start_iso DESC
LIMIT 20;
```

**Find Orphaned Events (Lacking Intent Fulfillment):**
```cypher
MATCH (e:Event)
WHERE NOT (e)-[:FULFILLS]->(:Intent)
RETURN e.pillar, count(e) AS Orphan_Count
ORDER BY Orphan_Count DESC;
```
