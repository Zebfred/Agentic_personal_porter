# Architectural Pivot (April 17, 2026)

> **Role Context:** Authored by Paul (Senior Principal Engineer and LLM/RAG Architect)
> **Priorities:** Sovereign Code, <20-second human friction rule, Neo4j graph relationships, MongoDB staging.

This document outlines the major architectural pivot for the Agentic Personal Porter project, addressing the structural, agentic, frontend, and observability layers following recent request loop crashes and scope modifications.

---

## 1. Data Infrastructure (MongoDB & Neo4j)

### Native MongoDB Time-Series Collections
To establish robust chronological tracking, we are integrating native MongoDB Time-Series collections. 

- **Calendar Ingestion Strategy:** We have implemented a sliding-window calendar ingestion process for both current and historical events. The ingestion script will manage batch pulls of current events and a rolling chronological fetch of historical events.
- **New Time-Series Collection Specification:**
  - **Collection Name:** `calendar_events_timeseries`
  - **Use Case:** Storing raw and processed calendar events optimized for temporal queries.
  - **Schema Considerations:** TimeField (`start_time`), MetaField (`event_type`, `pillar`), and measurements (`duration_minutes`).
- **Socratic Mirror Scope refinement:** The Mirror's integration with the data infrastructure is strictly pared down to categorizing Intention vs. Actual events across the defined 9 hero pillars.
- **Scalability & Rate-Limiting:** To handle high-frequency event ingestion by the `first_serving_porter`, we are introducing an exponential backoff queueing mechanism (e.g. Redis/Celery queue or strict batch-processing intervals) to buffer API calls to the LLM when processing hundreds of events.

---

## 2. Data Infrastructure: Vector Database Migration

- **Scale Beyond ChromaDB:** As the document parsing and historical logs grow, eventually migrate from a local SQLite/Chroma instance to a fully managed, production-grade Vector Database (e.g., Pinecone, Weaviate, or Qdrant).
- **Human Verification Imperative:** This migration will definitively require rigorous human-in-the-loop verification strategies to ensure that the shift in semantic storage does not corrupt or arbitrarily hallucinate the Hero's historical contexts.

---

## 3. Agent Roster Restructure

The agent roster for immediate development is being flattened and restructured to prevent hallucination looping and reduce cognitive load on the LLM orchestrators.

### Socratic Mirror (Demoted)
- **Scope Reduced:** Strict categorization of Intention/Actual events into the 9 pillars.
- **Demotion:** The Socratic_Reflection_Agent is being removed as the deep "Delta" thinker. It is now a highly specific, low-latency categorization tool.

### Audit Agent (NEW)
- **Role (The "Inspector"):** Audits the categorizations proposed by the Socratic Mirror.
- **Interface:** The Audit Agent interfaces with the `first_serving_porter` to drive a new "Verification Dashboard" for the user.
- **Friction Rule:** Maintains the <20-second human friction rule by batching reviews once a day. The First Porter presents the Audit Agent's corrections, and the human simply clicks "Approve" or "Reject".

### The First-Serving Porter (Expanded Managerial Role)
- **Front-Man Manager:** Reads daily quotas and outputs 2-3 definitive daily recommendations for the user. Interacts as the primary bridge between the graph data constraints and human intent.

### Time_Keeper (NEW)
- **Role (Temporal Specialist):** Dedicated to handling temporal and chronological queries.
- **Function:** Interfaces directly with the Mongo Time-Series collection to overcome Neo4j's inherent sequential blindness, allowing the user to ask complex "when did I last..." or "how often do I..." questions efficiently.

---

## 3. Frontend UI Pivot

The frontend will evolve to handle broader chronological scopes without inflating payload sizes.

- **Adventure-Log Update:** The standing Adventure-Log will remain scoped exclusively to the current week.
- **Adventure-Calendar (NEW):** We are adding a flexible `Adventure-calendar` endpoint and UI component.
  - **Purpose:** Handling events that extend outside of the current week.
  - **Views:** Serves as the base for monthly, "last week", and "next week" chronological rolling views. 
  - **Benefit:** Significantly reduces frontend payload sizes by only fetching large dataset ranges when explicitly navigated by the user.

---

## 4. Observability, Monitoring & Error Prevention

Following recent crashes caused by infinite requesting loops (e.g., via the `first_serving_porter`), we are mandating heavy observability and backoff integrations to protect API quotas.

### Tracing Collections
- **`first_serving_traces` (NEW):** A MongoDB collection logging every task delegation from the lead porter. Contains: `trace_id`, `target_agent`, `prompt`, `agent_state`, and `token_count`.
- **`first_serving_porter_happenings` (NEW):** A logging collection specifically designated for first_serving_porter to track behavioral heuristics.

### Execution Frameworks & Safeguards
- **LangSmith Integration:** A strict requirement for integrating LangSmith (or equivalent) to trace the multi-agent crew execution, offering visual mapping of agent loops.
- **Strict Exponential Backoff:** Mandatory implementation of exponential backoff decorators built cleanly around all LLM/Groq/OpenAI calls.
- **Request Density Strategy:** 
  - Implementation of local token tracking counters in memory that forcefully trips an error/halt circuit if > X tokens are consumed in < Y minutes by any solitary agent, effectively severing "infinite loops." 
  - Implementing max-retries limit on tool selections to prevent agents from spiraling when confused.

---

*(Note: Ensure corresponding updates are cross-referenced in active domain tracking documents)*
