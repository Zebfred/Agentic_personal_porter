# Porter Project Core Functionality & Outstanding Roadmap

## 1\. Executive Summary & Overarching Intent

- **Meta-Goal**: Achieve core application functionality using highly cost-effective and efficient agents (a fast Vertex AI model for categorization/sorting and a human-in-the-loop audit agent) alongside a stable First Serving Porter.  
- **Meta-Purpose**: Minimize friction (aiming for the \< 20-second administrative limit) for the user in recording intentions and actuals to ensure the tool is integrated into daily life.  
- **Current Constraints**: Resolve the cold start problem using internally generated application data first, temporarily bypassing heavy external API dependencies like Google Calendar to stabilize FinOps and token spend.

---

## 2\. Core Usability Mandates (May 12 Specifications)

*Source: [(Draft0-AI Refined)Core\_usabilty, May 12](https://docs.google.com/document/d/1uC_XwxXUbucVzojpYqchwwlqc5VHSlYB9f6xqz8DzeY/edit?usp=drivesdk&ouid=101679300686136753465)*

### Issue 1: Future Intentions and Versioned Chains

- **Problem**: The old `/adventure_log` expected both future intentions and past actuals in a single log, preventing fluid adjustments throughout the day.  
- **The Fix**: Create `/Adventure_expectations` endpoint. This strips out everything except the Current Local Week setup and Daily Reflection, adding a "Current Intentions" card as unstructured text.  
- **The Neo4j State-Tree Logic**: Move away from flat intention nodes to a versioned chain:  
  - Node: `(:Intention {version: 1, created_at: timestamp})`  
  - Relationship: `(Day)-[:PLANNED_AT {sequence: 1}]->(Intention)`  
  - Variance Calculation: Delta ($\\Delta$) is calculated against the terminal intention in the chain: $\\Delta \= \\text{Actual} \- \\text{Intention}\_{terminal}$.

### Issue 2: MongoDB Pipeline Optimization & Clean Slate

- **Problem**: High token costs and data engineering inaccuracy in pulling raw Google Calendar entries.  
- **The Fix**: Establish a new MongoDB collection called `Porter_collections`. Pause the GCP calendar sync for now, focusing purely on establishing a robust internal pipeline: Core App Data \-\> MongoDB \-\> Neo4j.

### Issue 3: Agentic System Stabilization

- **Problem**: Kinks in First Serving Porter, Socratic Mirror, and GTKY Librarian are causing execution loops.  
- **The Fix**: Verify connections, tools, and local data sources so the existing agents work beautifully using only internally generated application logs, ensuring functional baseline operations.

---

## 3\. Outstanding Backlog & Core Engineering (From April 2026 Logs)

*Source: [Apr\_log](https://docs.google.com/document/d/18PsFyRWV5EyFGTS-A58PjsHKu25TpcnqjD_VFVMYO90/edit?usp=drivesdk&ouid=101679300686136753465)*

### A. Telemetry, Observability & Rate Limiting

- **Infinite Loop Protection**: Build a Gunicorn/WSGI-compatible observability layer. Create a MongoDB `first_serving_traces` collection to log agent states, token counts, and reasoning paths.  
- **Exponential Backoff**: Implement strict backoff decorators on LLM requests to avoid hitting Vertex AI rate limits (preventing the "too many requests" crashes).

### B. Multi-Tenant Re-Architecture & Gatekeeping

- **Security Isolation**: Migrate from hardcoded `HERO_NAME = 'Jimmy'` to a full multi-tenant schema using `user_email` and `username`.  
- **Credential Storage**: Move all secure credentials (API keys, credentials.json, token.json) strictly to a hidden `.auth/` directory excluded from Git history.  
- **IAM Hardening**: Tighten GCP service accounts to follow the principle of least privilege.

### C. GCal Ingestion & Idempotency Fixes

- **The Event Explosion Bug**: Resolve the sync logic error that caused 13k+ GCal events to flood the landing zone during local syncs. Enforce a strict GCal ID mapping to MongoDB `_id` to guarantee upsert idempotency.

---

## 4\. Environment & DevOps Milestones (From May 2026 Logs)

*Source: [May2026\_log](https://docs.google.com/document/d/15zvnqYUckf6D8IK_boar_iH37AyynzjmkKh_6bU9vUs/edit?usp=drivesdk&ouid=101679300686136753465)*

### A. Dependency & Test Suite Clean Sweep

- Purged heavy dependencies (`tensorflow`, `tf-keras`) from the environment.  
- Migrated the codebase to LangChain v1.x and LangGraph (`create_react_agent`).  
- Secured a 100% success rate (69/69) on the local test suite in the `agentic_porter` conda environment.

### B. Local Docker WSGI Simulation

- Build and boot the local container: `docker build -t agentic_porter .`  
- Verify that Gunicorn and the pre-installed torch/onnxruntime ABI checks load correctly inside GCE Spot VMs.

### C. GTKY Librarian JSON Format Fixes

- Disable the static "dry-run" placeholder. Modify GTKY agent Graph prompts to guarantee they output properly formatted JSON objects to let events transition from the staging collections to Neo4j.

---

## 5\. FinOps & Automated Billing Response

- **Spot VM Consolidation**: Host both the Neo4j instance and the lightweight Ollama embedding model on a single, consolidated Spot VM instance to keep infrastructure costs under $15/month.  
- **Budget Alerts & Kill Switch**: Set up Pub/Sub topics linked to programmatic budget notifications in GCP to trigger a Cloud Run kill-switch function if token limits or server runtimes spike.

---

## 6\. Actionable Step-by-Step Priority Path

1. **Docker Container Deployment**: Complete Phase 1 of the container simulation to isolate cloud Gunicorn failures.  
2. **Setup `/Adventure_expectations`**: Build the database/endpoint pathways in Flask and Neo4j for unstructured intentions.  
3. **Format GTKY Outputs**: Patch the LangGraph parsing rules to enable real data to write into `Porter_collections`.  
4. **Deploy Telemetry Traces**: Add Gunicorn execution logging to the MongoDB `first_serving_traces` collection.

