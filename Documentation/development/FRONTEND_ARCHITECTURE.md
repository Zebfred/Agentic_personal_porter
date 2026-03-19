# Frontend Architecture

The user interface of the Agentic Personal Porter operates as a lightweight, lightning-fast application designed to minimize user logging friction down to <20 seconds.

## Tech Stack
- **HTML5:** Semantic structure housing the "Hero's Dashboard."
- **Vanilla JavaScript (`app.js`):** Lightweight asynchronous state manager replacing heavy frameworks.
- **Tailwind CSS (`index.css`):** Utility-first styling avoiding massive external dependency trees.

## Component Layout

1. **The Core Layout (`index.html`)**
   - Built around the "Twin-Track" interaction model:
   - **Left Column:** *Intentions* - Automatically populated via the `fetchCalendarEvents(day)` API calls.
   - **Right Column:** *Actuals* - The input boxes for reality, supplemented by slider constraints for "Brain Fog" and a "Valuable Detour" checkbox.

2. **The Hero's Inventory (`inventory.html`)**
   - Functions as the leaderboard or RPG character sheet.
   - A grid layout fetching metadata from Neo4j (via the API) regarding Quests, Goals, Skill Logs, and Life Pillars.

## Asynchronous Data Flow
1. **On Load / Day Select:** The app listens for a Day `<select>` change. Upon change, it requests `/get_calendar_events` and pre-fills the Intention column, drastically reducing manual typing.
2. **On Submit:** `app.js` constructs the overarching `JSON` payload representing the `log_data` (Day, TimeChunk, Realities, Feelings).
3. **The Reflection Wait:** An asynchronous `fetch` request is routed to `/process_journal`. 
4. **HTML Sanitization:** Before the returned AI reflection string is loaded into the interface, `app.js` runs it through an `escapeHTML` utility function to prevent XSS payloads, updating line breaks into safe `<br>` variants prior to altering the actual un-editable DOM innerHTML.
