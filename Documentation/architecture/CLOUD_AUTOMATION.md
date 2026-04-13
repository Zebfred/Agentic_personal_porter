# Cloud Automation & Time-Series Pipeline

Mach 2 depends on an active stream of Google Calendar entries to power the Identity Graph. Because the Docker container is stateless in Cloud Run, we use **Google Cloud Scheduler** to trigger the calendar pull at a predefined interval.

## 1. The Architecture
- **Trigger Source:** Google Cloud Scheduler (Cron Job)
- **Target Endpoint:** `POST https://<YOUR-CLOUD-RUN-URL>/api/admin/sync_calendar`
- **Authentication:** `Authorization: Bearer <PORTER_API_KEY>`

When Cloud Scheduler sends the POST request, `app.py` authenticates the token, connects to the Google Calendar API, pulls the newest chunk of data into the MongoDB Landing Zone (`raw_calendar_events`), formats it into the time-series (`formatted_events`), and runs `MERGE` injection into the Neo4j Identity Graph dynamically.

## 2. Deploying the Cloud Scheduler Jobs

We utilize an automated shell script to deploy multiple Cron Jobs simultaneously, pulling securely from the `.auth/.env` config rather than hardcoding variables in instructions.

### The Scheduled Architecture
1. **The Calendar Pulse (`mach2-calendar-sync`):**
   - **Target:** `POST /api/admin/sync_calendar`
   - **Trigger:** Runs at 08:00 AM and 10:00 PM (0 8,22 * * *).
   - **Function:** Ingests "Ground Truth" events into the Mongo Landing Zone and merges them into Neo4j.
2. **The Vector DB Batch (`mach2-vector-sync`):**
   - **Target:** `POST /api/admin/vector_sync`
   - **Trigger:** Runs at 12:00 PM and Midnight (0 0,12 * * *).
   - **Function:** Selects the previous 12-hours of Mongo inputs and generates/syncs embeddings to Weaviate and ChromaDB.

### Deployment Instructions
From the project root, simply run the setup orchestrator. Ensure that `GCP_PROJECT_ID` and `GCP_RUN_SERVICE_URL` are defined in your `.auth/.env`.
```bash
./setup_gcp_scheduler.sh
```

## 3. Log Diagnostics
You can monitor the automated pulls directly by checking the Cloud Run Logs or Cloud Scheduler Logs on the GCP Console. You can test your jobs manually without waiting via:
```bash
gcloud scheduler jobs run mach2-calendar-sync --location us-central1
```
