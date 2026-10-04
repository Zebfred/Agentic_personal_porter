# Frontend Architecture

The user interface of the Agentic Personal Porter operates as a lightweight, lightning-fast application designed to minimize user logging friction down to <20 seconds.

## Tech Stack
- **HTML5:** Semantic structure housing the "Hero's Dashboard."
- **Vanilla JavaScript (`app.js`, `script.js`, `artifacts.js`):** Lightweight asynchronous state managers replacing heavy frameworks.
- **Tailwind CSS:** Utility-first styling via CDN to avoid massive external dependency trees. Leveraging modern aesthetics like glassmorphism.

## Component Layout

1. **The Core Layout (`index.html`)**
   - Built around the "Twin-Track" interaction model:
   - **Left Column:** *Intentions* - Automatically populated via the `fetchCalendarEvents(day)` API calls.
   - **Right Column:** *Actuals* - The input boxes for reality, supplemented by slider constraints for "Brain Fog" and a "Valuable Detour" checkbox.

2. **The Hero's Inventory (`inventory.html`)**
   - Functions as the leaderboard or RPG character sheet.
   - A glassmorphic grid layout fetching mock and real metadata from the backend (`/api/inventory`) regarding Quests, Goals, Skill Logs, and Life Pillars. Managed by `script.js`.

3. **Hero Artifacts Management (`artifacts.html`)**
   - A dedicated UI mapping securely to JSON files (`hero_origin.json` and `hero_ambition.json`) via backend endpoints.
   - Operated by `artifacts.js`, taking a recursive dynamic form-builder approach to let the user update deeply nested origin and ambition metadata natively.

## Asynchronous Data Flow
1. **On Load / Day Select:** The app listens for a Day `<select>` change. Upon change, it requests `/get_calendar_events` and pre-fills the Intention column, drastically reducing manual typing.
2. **On Submit:** `app.js` constructs the overarching `JSON` payload representing the `log_data` (Day, TimeChunk, Realities, Feelings).
3. **The Reflection Wait:** An asynchronous `fetch` request is routed to `/process_journal`. 
4. **HTML Sanitization:** Before the returned AI reflection string is loaded into the interface, JS utilities run it through string filtering mechanisms to prevent XSS payloads prior to altering the actual un-editable DOM innerHTML.
