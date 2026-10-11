# 🗺️ Agentic Personal Porter: Future Evolution Plan

Provide a brief description of the problem, any background context, and what the change accomplishes.
This document serves as a strategic roadmap for the upcoming phases of the Agentic Personal Porter. It formally records recent infrastructure updates and outlines the conceptual designs for upcoming feature sets across the application's ecosystem.

---

## 1. Journal Review Endpoint Refactor (Completed & Documented)
The `journal_review.html` UI has been decoupled from the deprecated `adventure_log` payload structure.
- **New Endpoint**: A dedicated `GET /api/journal/review_data` endpoint was created in `journal_routes.py`.
- **Functionality**: It dynamically fetches stated "Hero Intentions" (aggregating data from `weekly_planning` and `hero_ambition.json`) and accurately maps "Actual Events" directly from the Mongo timeseries (`unified_events` and `event_actuals`).
- **Cleanup**: The deprecated "Push Truth to Google Calendar" UI element has been removed to align with our local-authority architectural shift.

---

## 2. Inventory System: Agentic Generation for Quests & Goals
The `inventory.html` page currently relies on passive data structures. We can introduce an **"Inventory Manager Agent"** (or expand the First-Serving Porter) to actively generate and curate these artifacts:

### Agentic Workflows for Quests & Goals:
* **Ambition Synthesis (Main Quests):** The agent can run a weekly cron-job that ingests `hero_ambition.json` and `weekly_planning`. It will synthesize these high-level desires into actionable, SMART-formatted "Quests" with predefined success criteria.
* **Detour Conversion (Side Quests):** The agent can analyze historical "Valuable Detours" from the time log. If it detects a recurring pattern of valuable behavior (e.g., spending 2 hours a week researching a new framework), it can automatically propose a new "Side Quest" to formalize that learning path.
* **Skill Progression:** By cross-referencing completed time chunks against the `category_mapping.json`, the agent can calculate "XP" and automatically increment levels in the Skill Log.

---

## 3. Graph Map Overhaul
**Current State:** The Identity Graph Map is currently a visually dense "hairball" that fails to convey actionable insights.
**Proposed Redesign:**
* **Hierarchical / Cluster Layouts:** Transition from a purely force-directed physics model to a clustered layout. Nodes should be grouped by Pillar (e.g., all "Health" nodes clustered together) or by Temporal Epochs (grouping by month).
* **Progressive Disclosure:** Implement node collapsing. By default, only core Pillar nodes and major Quests should be visible. Users can click to expand and reveal the underlying raw time chunks and journal entries.
* **Semantic Filtering:** Enhance the Node Inspector to filter by "Alignment Status" (showing only Detours or Fog of War) to quickly identify anomalies in the graph.

---

## 4. The Oracle Agent (Predictive Funnies & Analytics)
The Oracle endpoint is ready to evolve from a static placeholder into an active, predictive LLM agent. 

### Architecture for the Oracle:
1. **The Prediction Loop:** A daily background job (perhaps utilizing the new asynchronous event workers) will trigger the Oracle Agent. The agent will read the previous day's events, current weekly expectations, and historical patterns.
2. **The Output:** It will generate a daily prediction artifact (e.g., *"I foresee a 70% probability you will fall into a Fog of War regarding your 'Personal Projects' pillar around 3:00 PM."*).
3. **The Ledger of Truth:** Predictions will be stored in a new Mongo collection (`oracle_predictions`). At the end of the day, a secondary agent will compare the Oracle's prediction against the `event_actuals` to calculate an "Accuracy Score."
4. **Constant Improvement:** The Oracle's system prompt will be injected with its own historical accuracy scores, forcing the LLM to reflect on its predictive failures and refine its analytical approach over time.
