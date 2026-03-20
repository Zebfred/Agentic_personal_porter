# Active Security Tasks

This document serves as the master checklist and roadmap for the dedicated **Security Agent** responsible for hardening the Agentic Personal Porter's architecture. Because this is a public repository containing sovereign, highly personal data, closing these vectors is a top priority.

## 1. Secrets & Credentials Management
- [x] **Constant Data PII Extraction**: Moved the `ACTUAL_CATEGORY_MAPPING` out of `src/constants.py` and into the git-ignored `.auth/category_mapping.json` to prevent personal pillars/goals from leaking into the public repo. Created a dummy `data/category_mapping.example.json`.
- [ ] **Secure Token Storage**: The Google Calendar OAuth flow currently uses `.pickle` to store tokens. This is intrinsically insecure and must be migrated to a secure database or an encrypted `.json` format within the strict `.auth/` quarantine.
- [ ] **Enforce `.auth/` Isolation:** Under no circumstances should any `.env`, `credentials.json`, `token.json` or mapping files reside in the project root. All such artifacts must be strictly quarantined within the `.auth/` directory.

## 2. Authentication & Authorization
- [ ] **Implement True AI/User Authentication**: The Flask API (e.g., `/process_journal`) is currently fully open with no auth, and the Neo4j database relies on a hardcoded user ID. We must implement JWT, OAuth, or Flask-Login to support secure, multi-user deployments.
- [ ] **Restrict CORS**: Explicitly bind the Cross-Origin Resource Sharing (CORS) policy to internal or trusted domains only (e.g., strictly `localhost:5000` or the eventual production domain).

## 3. PII Log Sanitization
- [ ] **No Raw Output in Production**: Ensure that development functions relying on `print(journal_entry)` or `print(log_data)` to standard output (`stdout`) are fully suppressed in production (`server.py` and `rag_system`).
- [ ] **Data Minimization**: AI agent reflections must only extract and store features specifically designed for the Hero's Inventory or the Neo4j Graph, silently discarding irrelevant PII.

## 4. Frontend XSS Mitigations
- [ ] **Escape Client Output**: All incoming AI reflections delivered to `app.js` must be run through rigorous HTML escaping before being injected into the DOM. Never use raw `innerHTML` without intermediate sanitization logic (convert `\n` to `<br>` safely).
- [ ] **Local Storage**: Store raw text, not rendered HTML, to guarantee consistent sanitization behavior across subsequent session loads.

## 5. Input Validation
- [ ] **Strict Route Filtering**: The Flask `/process_journal` and FastAPI `/query` endpoints must enforce rigorous JSON schema assertions. Verify types and block the ingestion of severely malformed nested arrays or deeply injected commands.
- [ ] **Calendar Validation**: Any events ingested automatically via the `/get_calendar_events` endpoint must similarly be sanitized prior to hitting the AI execution block or graph DB.

## 6. Production Environment Configurations
While the current MVP operates effectively on a local Flask developer server, any future deployment must include the following architecture modifications:
- [ ] **Gunicorn / uWSGI**: Transition the Flask development server to a hardened WSGI application server.
