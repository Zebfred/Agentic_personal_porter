# Active Code Hygiene & Refactoring

This document tracks technical debt, codebase cleanup, and structural optimizations that must be maintained to ensure the application scales smoothly without collapsing under its own weight.

## Current Priorities

- [x] **Neo4j Massive Refactor:** The `neo4j_db.py` file has bloated to over 400 lines. Break it down using an **Inheritable Agent Strategy** or modular class-based architecture to separate connection logic, read operations, and write/merge pipelines. *(Pending Human Verification)*
- [x] **Sanitize Global Data Exposure:** Continue auditing the `src/` directory to hunt for hardcoded PII. Move any remaining personal configuration files into the `.auth/` quarantine pattern. *(Moved hero_considerations.json to .auth/hero_detriments.json, sanitized PII names. Pending Human Verification)*
- [x] **Backend API Standardization:** Migrate arbitrary Flask routes toward strict RESTful or GraphQL paradigms with rigorous Pydantic schema validation. *(Pending Human Verification)*
- [x] **Consolidate GCal Scripting:** `inject_hero_calendar.py` and `inject_hero_foundation.py` exist as standalone scripts. They need to be cleanly integrated as scheduled background workers or modular API tools driven by the frontend. *(Included as Admin API routes in app.py. Pending Human Verification)*
- [x] update our test suite *(Added test_api_schemas.py and test_neo4j_client.py. Pending verification)*
- [x] verify all files that produce logs files are placing them in the logs directory *(Replaced print() with file-backed Logger in app.py, moved stray log files to logs/legacy/. Pending verification)*