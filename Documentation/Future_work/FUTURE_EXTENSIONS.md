# Future Platform Considerations
> This document tracks long-term, out-of-scope, or highly complex features that are approved for future roadmaps but should not distract from current sprint deliverables.

## Browser Extension Architecture
- **Goal:** Transform the web app into a robust Chrome/Browser extension for deeply native calendar integration and background tracking.
- **Why Deferred:** To avoid extension-specific manifest constraints and cross-origin authentication pain points during early UI prototyping.
- **Future Reqs:**
  - Build `manifest.json` using Manifest V3 parameters.
  - Port `auth.js` session storage logic to `chrome.storage.local`.
  - Handle background workers for calendar sync instead of explicit "Sync" buttons.
  - Implement a persistent side-panel or pop-up interface for the `index.html` hub.

## Multi-User Authentication & Login Architecture
- **Goal:** Transition from a single global API key to a secure, multi-tenant application supporting individual Username/Password logins.
- **Why Deferred:** Introduces massive architectural overhead. Currently, the database makes direct queries based on a global environment variable (`HERO_NAME`). To properly adopt a multi-user login, all backend connections must be refactored so MongoDB documents and Neo4j Identity Graph nodes are bounded to a specific `user_id`.
- **Future Reqs:**
  - Create a new `users` collection in MongoDB for `username`, `email`, and securely hashed passwords (using Flask's `werkzeug.security`).
  - Develop `/api/register` and `/api/login` endpoints to validate against the Mongo hash and issue JWTs featuring `user_id`.
  - Refactor `@require_auth` to decode the JWT and bind `user_id` to the context of subsequent database requests.

## Bidirectional Google Calendar Sync (Agent-Controlled Ghost Calendars)
- **Goal:** Utilize Google Calendar API service account scopes to create and post to new, secondary calendars on behalf of the user, separating our system's tracked data from their main, unaltered calendar.
- **Why Deferred:** Requires complex multi-calendar API logic, dedicated service account configurations, and robust agent scheduling flows to avoid spamming the Google Calendar API quotas.
- **Future Reqs:**
  - Build an agent flow that ingests all events from the user's primary calendar (read-only, ensuring no disruption to their native workflow).
  - Use our agentic data layers to automatically generate three distinct "Ghost Calendars" within the user's Google Workspace:
    1. **Intent Calendar:** Displaying the user's original planned events/goals.
    2. **Actual Calendar:** Displaying the post-reflection reality of how the time was spent.
    3. **Matched/Mismatch Calendar:** A heatmap or strictly diff-based calendar visualizing the delta between Intent and Actual time usage.
  - Implement dynamic sync pipelines to push our Neo4j/MongoDB refined data outwards to these newly generated Google Calendars.

  **Detailed Technical Implementation Path:**
  - **Frontend Changes:**
    - Explicit UI toggle in settings to "Initialize Porter Calendars".
    - Status dashboard visualizing the outbound sync health.
    - Ensure OAuth flow requests full `https://www.googleapis.com/auth/calendar` scope.
  - **Backend Changes:**
    - Integration module using `calendars.insert` API to provision the 3 calendars.
    - Outbound `push_graph_to_calendar.py` orchestrator triggered on a cron-job to batch update Google.
    - Algorithm to compute the Intent vs. Actual delta and assign Google Calendar color IDs accordingly.
  - **Agentic System Upgrades:**
    - A specific Agent task designed to generate a concise "Delta Summary" explaining the difference between Intent and Actual.
    - Agent-agnostic architecture: Agents write to Mongo, and the Backend handles the API pushing to avoid quota exhaustion.
  - **Required Data Model Additions:**
    - User Profiles (MongoDB): Must store the newly generated `calendarId` strings for the three Ghost Calendars.
    - Event Documents (MongoDB): `event_intentions`, `event_actuals`, and `unified_events` will need a new tracking field (e.g., `gcal_pushed: boolean` and `gcal_push_timestamp`) to ensure idempotency and prevent duplicate API calls during outbound syncs.


## Intelligent Journal & Document Mining (Personal & Corporate Porter)
- **Goal:** Ingest, parse, and intelligently map unstructured text from Google Docs and daily journals into the Neo4j Identity Graph, moving beyond simple scheduling data into rich, contextual "thoughts and feelings" data.
- **Why Deferred:** Parsing unstructured data spanning 6+ years with highly variable formats (Month Year, Month Day, military time) requires a specialized NLP pipeline, chunking strategy, and potentially a dedicated vectorization agent.
- **Future Reqs:**
  - **Specific Use Case (Personal):** Build a dedicated Python parser that connects to the Google Drive API, identifies documents matching the user's specific naming conventions (e.g., `Month Year`, `2nd_itter_PP_April`, `Tech Thinking April 2026`), and chunks them using their specific military time (`NN:NN`) delimiters.
  - **General Scope (Corporate Porter Framework):** To make this work for anyone, the ingestion agent needs to be "format-agnostic." We would use an LLM pre-processor that "reads" a sample of a user's document, infers their structural logic (headers, dates, timestamps), and dynamically generates a regex/chunking strategy to parse the rest of the document.
  - **In-House Feature:** For users without 6 years of Drive data, we must build a native, frictionless "Daily Journal" UI directly into the Personal Porter Hub. This UI should actively prompt the user with questions based on their calendar events (e.g., "You just had a meeting about X, what are your thoughts?"), lowering the barrier to entry and keeping the data natively formatted for our graph.