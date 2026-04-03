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
