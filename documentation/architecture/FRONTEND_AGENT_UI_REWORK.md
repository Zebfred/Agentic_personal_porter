# Frontend Technical Debt: Agent-Controlled Actions UI Rework

## Overview
During the Multi-Tenant OAuth Portals refactor, the **Identity Graph Pulses** and **Verification Dashboard** sections were removed from the standard user `index.html` portal and migrated to the `admin_index.html` hub. This was done to sanitize the standard user experience and ensure administrative/system-level metrics were not leaked to standard users while the backend was still operating with global credentials.

However, these cards originally represented agent-controlled actions specific to the user (e.g., "Valuable Detours", "Logged Reflections", and "Needs Review" audits). 

## Required Rework
Once the backend and agent orchestration layers have been fully refactored to be strictly user-aware (multi-tenant) at the CrewAI and Agent level, these UI components must be reinstated and reworked for the user portal:

1. **User-Specific Identity Graph Pulses**:
   - The user needs to see their own metrics (their synced events, their detours, their reflections).
   - This requires an endpoint (e.g., `/api/user/pulse`) that queries MongoDB/Neo4j strictly scoped to the user's `email`.

2. **User Verification Dashboard**:
   - Users should have the ability to review low-confidence classifications made by the GTKY Librarian or other agents *specifically on their own calendar events*.
   - Currently, the Verification Dashboard (`/api/admin/unverified_audits`) requires an `admin` role and fetches global data.
   - We will need a new `/api/user/unverified_audits` endpoint that fetches only `status: "Pending Verification"` events belonging to the user.

## Implementation Notes
- **Location**: These reworked cards should likely be placed back into `frontend/index.html` (potentially replacing or sitting alongside the newly added "Adventure Log" overview).
- **Backend Dependency**: **[COMPLETED]** The backend data-layer partition (Silas Audit Remediation) has been fully executed. `SovereignGraphInjector`, `GTKYLibrarian`, and all `uuid_manager` events now strictly support `user_email` partitioning. The next step is building the explicit API endpoint routes (`/api/user/pulse`, `/api/user/unverified_audits`) to expose this safely to the frontend without breaking boundaries.
