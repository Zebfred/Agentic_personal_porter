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
