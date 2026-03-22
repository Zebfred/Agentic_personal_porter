# Active Frontend Development

This document tracks immediate, actionable tasks for the frontend interface (`app.js`, `index.html`, `inventory.html`).

## Highest Priority: Hero Artifacts Management UI
*Status: Architecture conceptualized, UI completely missing.*

- [x] **Artifact Builder UI:** Create a dedicated, polished frontend interface allowing the user to seamlessly view, build out, and manually update their core hero artifacts (specifically `hero_origin.json` and `hero_ambition.json`). (Awaiting human verification)
- [ ] **Proactive Refinements (Future Work):** Implement a mechanism to proactively prompt the user during their daily recon to fill out missing artifact sections or provide minor refinements over time.

## Secondary Priority: The Hero's Inventory Overhaul
*Status: Placeholders set, but no actual development.*

- [x] **Dynamic Injection:** Ensure the "Valuable Detours" `<div>` (`#valuable-detours-list`) successfully handles dynamic injection from the backend without breaking the new CSS grid. (Awaiting human verification)
- [x] **Quests & Goals:** Replace the empty placeholder with actual fetch logic bridging to Neo4j `Intention` pathways. (Awaiting human verification)
- [x] **Skill Log:** Build out the UI component that maps to newly acquired `Achievement` nodes. (Awaiting human verification)
- [x] **Equipment & Knowledge Repository:** Build out the UI component mapping to stored artifacts and notes. (Awaiting human verification)
- [x] **Hero's Stats:** Design a visual representation (e.g., progress bars, radar charts) quantifying user growth from "Hero Numbers." (Awaiting human verification)
- [x] **Finances:** Create a specialized input/display tool for tracking financial variables aligned with quest goals. (Awaiting human verification)
- [x] **Origin/Ambition Collection:** Develop entirely new UI input variants designed strictly to capture the user's "Origin Story" and "Long-term Ambitions" for the GTKY agent context. (Awaiting human verification)

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
