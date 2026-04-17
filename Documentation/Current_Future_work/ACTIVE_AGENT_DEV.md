# Active Agent Development

This document specifically scopes the requirements, prompts, and networking logic for our core Agentic ecosystem.

## 1. The First-Serving Porter
*Status: Requirements drafted below.*
- [ ] **Primary Interface:** Serve as the direct, chat-based interface for the user natively deployed on the Hub (`index.html`).
- [ ] **Goal Metrics Interaction:** Be capable of synthesizing and intelligently communicating the user's progress against the Identity Graph (Neo4j).
- [ ] **Artifact Maintenance:** Proactively identify "holes" in the user's `hero_origin.json` or `hero_ambition.json` and engage the user specifically on those incomplete strings.
- [ ] **Agent Orchestration:** Intelligently route user feedback to other sub-agents (e.g., the Journaling Classifier or the future Oracle agent).
- [ ] **Transparency Tracker:** The frontend must visibly log and explain *when* and *why* the First-Serving Porter is communicating with a downstream agent to ensure total transparency.

## Imminent Development Tasks
- [ ] Draft system prompt for the First-Serving Porter.
- [ ] Connect the agent to the Neo4j reader endpoint so it can pull down the user's active graph data.
- [ ] Define the inter-agent communication payload structure (how the Porter sends task requests to the classifier agent).

## The Oracle Predictions Agent (Future Feature)
*Status: Placeholder architecture.*
**Mandate:** Predict possible paths of action for the hero to take to be successful given their goal for the week, their general intent, and historical data. This is intended to be a novel "fun" feature for now, as it is expected to be relatively poor at its job initially without massive fine-tuning.

## The Corrector Porter (Hallucination Audit)
*Status: Requirements drafted. Preliminary setup created in `vector_storage.py`.*
- [ ] **Audit Mandate:** Acts as the final quality assurance chokepoint. Checks the Socratic/First-Serving drafted response against the Vector DB (Intuitive Memory) to definitively ensure the agent hasn't hallucinated a goal the user never set or made a repeated historical mistake.
- [ ] **Preliminary Testing:** Run initial chunking and similarity search testing (Atlas Vector Search) on `Semantic_vectors` to give the Corrector and GTKY agents access to historical "vibes".

## Audit Agent (NEW - The Inspector)
*Status: Architecture defined.*
- [ ] **Verification Logic:** Audits the categorizations proposed by the Socratic Mirror.
- [ ] **Verification Dashboard Interface:** Interfaces with `first_serving_porter` to drive a low-friction verification dashboard. Batch reviews once a day where human user simply clicks "Approve" or "Reject".

## Time_Keeper (NEW - Temporal Specialist)
*Status: Architecture defined.*
- [ ] **Chronological Querying:** Dedicated to temporal queries, overcoming Neo4j's sequential blindness by interfacing with the Mongo Time-Series collection directly.

## Socratic Mirror (Demoted)
*Status: Scope refinement pending implementation.*
- [ ] **Scope Reduction:** Stop usage as a deep contextual "Delta" thinker. Strictly reduce to categorization of Intention vs. Actual events across the 9 defined pillars.

## Observability & Error Prevention
*Status: High Priority post-crash mandate.*
- [ ] **Multi-Agent Tracing:** Mandate the integration of LangSmith (or equivalent framework) to trace crew execution and identify infinite reasoning loops.
- [ ] **Backoff Decorators:** Implement and enforce strict exponential API rate-limit backoff decorators on all LLM inference calls to manage quotas and prevent "request explosions."

## Architectural Workflows
- [ ] **Implement SLM Triage Logic:** Integrate a localized/cheap SLM (like Llama 3 or Mistral) to rapidly classify 90% of routine tasks (Meals, Sleep), only waking up the heavy CrewAI Agentic cluster for "Uncertain" gaps or complex "Delta" logic.
- [ ] **The "Hero Cycle" Orchestration Pipeline:** Explicitly code the 5-step lifecycle pipeline: Ingestion (Sense) -> Contextual Retrieval (Think) -> Collaborative Reasoning (Plan) -> Verification (Audit) -> Execution (Act).

## Verifying the Agents (The "Daily Recon" Audit)
To make sure the agent isn't hallucinating your productivity, use Evaluation Loops assisted by an LLM-as-a-Judge (likely the First-Serving Porter or a second LangChain Porter):
- **Golden Dataset:** Take 20 of your "Daily Recon" verifications (where you clicked Yes/No) and store them as "The Truth."
- **Shadow Testing:** Every time you update your agent's prompt, run it against those 20 events. If its classification (e.g., "Valuable Detour") doesn't match your manual label, the "Judge" agent flags it.


1. Small Language Models (SLMs) for Classification
You don't need a massive model to tell you that "Dog walk" belongs to the "Health/Maintenance" pillar.

The Strategy: Use a local or cheaper model (like Llama 3 or a small Mistral model) for Initial Triage.

The Flow:

SLM: Categorizes 90% of routine tasks (Sleep, Meals, Repeating meetings).

Agentic Crew: Only gets triggered for the "Gaps" or complex "Delta" logic that the SLM flags as "Uncertain."