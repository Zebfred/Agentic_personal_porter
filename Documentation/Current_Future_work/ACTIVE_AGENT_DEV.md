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
