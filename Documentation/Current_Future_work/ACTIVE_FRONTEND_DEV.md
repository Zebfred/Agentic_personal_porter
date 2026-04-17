# Active Frontend Development

This document tracks immediate, actionable tasks for the frontend interface (`app.js`, `index.html`, `inventory.html`).

## Highest Priority: Frontend Hub Overhaul
*Status: UI Scaffolding complete - Merged to main*

- [ ] **The Porter Hub (`index.html`):** Convert the index into a central dashboard displaying Identity Graph metrics, a "Sync Calendar" action, and an interactive Agent chat interface that queries missing hero artifacts. *(Pending backend and Agent development)*
- [x] **Adventure Time Log (`Adventure_Time_log.html`):** Migrate the current daily 20-minute chunking UI out of the index and into this dedicated route. Retain scope explicitly for the *current week*.
- [ ] **Adventure Calendar (NEW):** Build a flexible `Adventure-calendar` endpoint and UI component. This will serve as the base for monthly, "last week", and "next week" rolling views chronologically while keeping frontend payload sizes low.
- [ ] **Historical Journal Review (`journal_review.html`):** Build a dedicated interface for evaluating past journal entries and grading agent classifications. *(Pending backend and Agent development)*
- [ ] **Verification Dashboard (NEW):** Simple "Dashboard of Inferences" interfacing with the Audit Agent. Updates of First Porter present corrections; user explicitly clicks "Approve" or "Reject". Enables <20-second human friction rule.
- [ ] **Oracle Predictions (`Oracle_predictions.html`):** Create a placeholder UI for future predictive agent features. *(Pending backend and Agent development)*
- [ ] **Weekly Goal Artifact Selector:** Build a simple UI module on the Hub allowing the user to explicitly define the "Priority Pillar" for the current week, setting the weights for backend agent logic.

## Highest Priority: Hero Artifacts Management UI
*Status: Architecture conceptualized, UI completely missing.*

- [x] **Artifact Builder UI:** Standardized API paths to relative URLs, resolving CORS issues. Artifacts securely viewable and updatable via the new interface.
- [ ] **Proactive Refinements (Future Work):** Implement a mechanism to proactively prompt the user during their daily recon to fill out missing artifact sections or provide minor refinements over time.
- [ ] **Future Artifact Builder (`hero_future.json`):** Create UI input variants specifically designed to capture the user's ambitions over distinct periods of time (short, mid, and long term).

## Secondary Priority: The Hero's Inventory Overhaul
*Status: UI overhaul developed but currently non-functional.*

- [x] **Dynamic Injection:** Successfully connected and debugged the inventory injection logic using relative API paths and expanded CORS support.
- [ ] **Quests & Goals:** Debug fetch logic bridging to Neo4j `Intention` pathways.
- [ ] **Skill Log:** Debug the UI component mapping to `Achievement` nodes.
- [ ] **Equipment & Knowledge Repository:** Debug UI component for artifacts/notes.
- [ ] **Hero's Stats:** Debug visual representation logic.
- [ ] **Finances:** Debug financial tracking variables.
- [ ] **Origin/Ambition Collection:** Debug the Origin Story frontend data handlers.

## Tertiary Priority: Finalize the "Daily Recon" UI (Mach 2)
*Status: Missing from active development tracker, importing from Mach 2 Roadmap.*

- [ ] **The 20-Second Verification Loop:** The frontend (`index.html` / `app.js`) must be optimized to prioritize lightning-fast daily verification of the twin-track data.
- [ ] **Low Cognitive Load:** Agent-inferred labels for activities (from the Mongo staging) must be visibly flagged on the frontend, easily correctable by the user, and confirmable with a single click.
- [ ] **Artifact UI Hook:** Update the `inject_hero_foundation` logic to pull smoothly from the new Artifact Management UI rather than existing strictly as a backend dev script.

## Upcoming Priority: Formal Production Login System
*Status: Completed and awaiting human verification.*

- [x] **Authentication UI:** Design and build a secure, polished login and registration screen for the application. (Awaiting human verification)
- [x] **Session Management:** Implement frontend token handling (e.g., JWT) securely stored in memory or HTTP-only cookies, replacing the current prompt-based local storage API key method. (Awaiting human verification)
- [x] **Route Protection:** Ensure all frontend pages proactively check authentication state and redirect unauthenticated users to the new login screen. (Awaiting human verification)
Building a proper user login