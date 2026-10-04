# Security and Safety Checklist

The Agentic Personal Porter acts as a guardian of highly personal sovereign user data. Because the codebase operates as a public repository, prioritizing safe development practices and rigorous data obfuscation is paramount. 

All future development must adhere to the following checklist.

## 1. Secrets & Credentials Management
- [ ] **Enforce `.auth/` Isolation:** Under no circumstances should any `.env`, `credentials.json`, `token.json` or `.pickle` file reside in the project root. All such artifacts must be strictly quarantined within the `.auth/` directory.
- [ ] **Git Exclusion:** Ensure `.auth/` and any local database state (e.g., `data/chroma_db`) remain fully excluded in the `.gitignore` and `.cursorignore` files.
- [ ] **Secret Management Library:** Leverage configurations explicitly routing environment retrievals through non-indexed path definitions.

## 2. PII Log Sanitization
- [ ] **No Raw Output in production:** Ensure that development functions relying on `print(journal_entry)` or `print(log_data)` to standard output (`stdout`) are fully suppressed in production (`server.py` and `rag_system`).
- [ ] **Data Minimization:** AI agent reflections must only extract and store features specifically designed for the Hero's Inventory or the Neo4j Graph, silently discarding irrelevant PII.

## 3. Frontend XSS Mitigations
- [ ] **Escape Client Output:** All incoming AI reflections delivered to `app.js` must be run through rigorous HTML escaping before being injected into the DOM. Never use raw `innerHTML` without intermediate sanitization logic (convert `\n` to `<br>` safely).
- [ ] **Local Storage:** Store raw text, not rendered HTML, to guarantee consistent sanitization behavior across subsequent session loads.

## 4. Input Validation
- [ ] **Strict Route Filtering:** The Flask `/process_journal` and FastAPI `/query` endpoints must enforce rigorous JSON schema assertions. Verify types and block the ingestion of severely malformed nested arrays or deeply injected commands.
- [ ] **Calendar Validation:** Any events ingested automatically via the `/get_calendar_events` endpoint must similarly be sanitized before hitting the AI execution block or graph DB.

## 5. Production Environment Prerequisites
While the current MVP operates effectively on a local Flask developer server, any future public cloud deployment must include the following architecture:
- [ ] **Gunicorn / uWSGI:** Swap to a hardened WSGI application server.
- [ ] **Restrict CORS:** Explicitly bind the Cross-Origin Resource Sharing policy to internal or trusted domains only.
- [ ] **Agentic Authentication:** Add JWT endpoints or OAuth layers preventing unauthorized database injection runs on the web app.
