# Quickstart & Visual GUI Verification Guide: `003-first-serving-hub-api`

**Feature Branch**: `003-first-serving-hub-api`  
**Date**: 2026-10-25

---

## 1. Run Offline Unit & Contract Tests ($0.00 Cloud Cost)

Verify all endpoints, Pydantic v2 schemas, `events_to_be_classified` staging queue, `/api/user/hub_metrics`, `/api/planning`, `hero_origin.json` & `hero_ambition.json` missing-artifact scans, `saga_status` journal history, and the Jira ↔ Jules Hub GUI status endpoint:

```bash
uv run pytest tests/unit/test_first_serving_hub_api.py -v --tb=short
make verify-done
make test-roster
```

---

## 2. Live Browser GUI Verification (Porter Hub & Jira ↔ Jules Command Center)

1. **Start the local development stack**:
   ```bash
   make build-css
   uv run python src/app.py
   ```
2. **Open the Porter Hub in your browser**:
   - **Hero Hub**: `http://localhost:5001/index.html` (or `http://localhost:5001/`)
   - **Nexus-Guild Admin Hub**: `http://localhost:5001/admin_index.html`
3. **Verify the 4 Interactive Hub Capabilities in the GUI**:
   - **Adventure Log / Hub Progress Metrics (`/api/user/hub_metrics`)**: Inspect real-time counts for *Intentions Logged*, *Calendar Events Logged*, *Events to be Classified*, *Matched Intentions*, *Valuable Detours*, and the week-over-week *Detrimental Detours* delta badge (`↓ %`).
   - **One-Shot Weekly Planning (`/api/planning`)**: In the *Current Week Trajectory / Quick Plan* card, submit a multi-line weekly intention plan and see the Hub counters and weekly trajectory update immediately.
   - **Missing Artifact Scans (`/api/artifacts/scan`)**: View automatically detected gaps across both `hero_origin.json` and `hero_ambition.json` and send gap responses to the First-Serving Porter with 1 click.
   - **Spec-Kit / Jira ↔ Google Jules Command Center (`/api/integrations/jira/status`, `/speckit-push`, `/jules/dispatch`)**:
     - See the active Spec-Kit feature (`003-first-serving-hub-api` or `002-jira-jules-bridge`), readiness pills (`Jira API` & `Jules CLI`), and parsed `T001`+ tasks with persona badges (`sentinel`, `bolt`, `palette`, `archie`, `docdoc`, `dave`, `crii`, `jovol`, `silas`).
     - Click **"Push Spec-Kit Tasks to Jira"** (dry-run or live) to stage/sync tasks.
     - Select any task and click **"Preview Work Order"** to view the complete formatted prompt (with `.agents/roster/<persona>.md` directives and verification gates) directly inside the GUI drawer, or click **"Dispatch to Jules"** to launch a Jules session.
