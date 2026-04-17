# Deployment Checklist

This document provides a comprehensive checklist for releasing the Agentic Personal Porter to a production environment (such as Google Cloud Run). Use this to ensure all security, stability, and authentication measures are verified prior to deployment.

## 1. Pre-Deployment Configuration and Code Hygiene

- [ ] **Dependency Audit:** Verify that `requirements.txt` is updated with all recently added libraries (e.g., `google-api-python-client`, `google-auth-oauthlib`, `gunicorn`).
- [ ] **CORS Settings:** Confirm that CORS origins are strictly defined. Wildcard `*` origins should be removed in favor of explicit domain/port lists in `src/app.py`.
- [ ] **WSGI Server:** Ensure the `Dockerfile` and local production runners (`run_production.sh`) are utilizing a production-grade WSGI server like **Gunicorn**, and *not* the built-in Flask dev server.
- [ ] **Environment Path Resolution:** Verify `src/utils/path_utils.py` and `src/config.py` have fallback paths setup for loading `.env` variables from volume mounts (e.g., `/.auth/Porter_auth_env` or `/.auth/.env`).

## 2. Secrets and Authentication Readiness

- [ ] **API Keys Configured:** Ensure the primary Secret Manager houses all required tokens:
  - `GROQ_API_KEY`
  - `MONGO_URI`
  - `NEO4J_URI` (Must use the `neo4j+s://` scheme)
  - `NEO4J_USERNAME` / `NEO4J_PASSWORD`
  - `PORTER_API_KEY` (The master key required for endpoint authorization via `Bearer` tokens).
- [ ] **Endpoint Protection:** Verify that `@require_api_key` decorators are applied to sensitive routes like `/process_journal`, `/api/inventory`, and `/get_calendar_events`.
- [ ] **Google Calendar Authorized:** Ensure `credentials.json` and the corresponding `token.json` are properly mounted or accessible through the environment parameters.

## 3. Infrastructure Targets

- [ ] **Docker Timeouts & Memory Restrictions:** Ensure `Dockerfile` defines an extended `gunicorn` `--timeout 300` threshold to permit large batch operations, and that Cloud Run deployments specify adequate memory minimums (e.g., `--memory 1024Mi`).
- [ ] **Deployment Script & Secrets:** Verify `sync_secrets_gcp.sh` has successfully populated GCP Secret Manager, allowing `deploy_gcp.sh` to securely deploy with the native `--set-secrets` argument.
- [ ] **Container Build:** If using automated Git triggers (Cloud Build), confirm that the CI/CD pipeline correctly builds the updated `Dockerfile` container upon merge to `main`.

## 4. Post-Deployment Validation

- [ ] **Health Check:** Hit the base URL or index to confirm the instance is responsive and the container booted successfully.
- [ ] **Authorization Test:** Send an intentionally unauthenticated POST/GET request to `/api/inventory` or `/process_journal` and confirm a `401 Unauthorized` is returned instead of executing the function.
- [ ] **Database Connection Validation:** Run a diagnostic script or verify application logs to ensure successful handshakes with MongoDB and Neo4j.
- [ ] **Agentic Crew Logic:** Submit a sample journal entry and confirm the CrewAI reflection pipeline outputs a formatted response without internal server errors (500).
