# Known Issues

This document tracks identified bugs, unverified architectures, and technical debt that require immediate attention or verification before the next major release.

- [ ] **Neo4j Connection Verification:** Neo4j connections and graph relationship logic need to be rigorously verified to ensure they match current Mach 2 architectural expectations (Idempotency, correct mapping of Intent vs. Actual).

## Frontend UI & Data Loading Issues
- [ ] **Artifacts Display (`/artifacts.html`):** The *Ambition & Intent*, *Hero Detriments*, and *Pillars Mapping* sections all have issues correctly displaying their data.
- [ ] **Journal Review Data Load (`/journal_review`):** Has issues loading data due to timeseries arrays being empty. 
- [ ] **Graph Explorer UX (`/graph_explorer`):** The interface is cluttered and unreadable, requiring visualization improvements.
