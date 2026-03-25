# Cloud Automation & Time-Series Pipeline

Mach 2 depends on an active stream of Google Calendar entries to power the Identity Graph. Because the Docker container is stateless in Cloud Run, we use **Google Cloud Scheduler** to trigger the calendar pull at a predefined interval.

## 1. The Architecture
- **Trigger Source:** Google Cloud Scheduler (Cron Job)
- **Target Endpoint:** `POST https://<YOUR-CLOUD-RUN-URL>/api/admin/sync_calendar`
- **Authentication:** `Authorization: Bearer <PORTER_API_KEY>`

When Cloud Scheduler sends the POST request, `app.py` authenticates the token, connects to the Google Calendar API, pulls the newest chunk of data into the MongoDB Landing Zone (`raw_calendar_events`), formats it into the time-series (`formatted_events`), and runs `MERGE` injection into the Neo4j Identity Graph dynamically.

## 2. Deploying the Cloud Scheduler Job

Using the GCP CLI (`gcloud`), you can create the automated job perfectly:

```bash
# Set your variables
export PROJECT_ID="agentic-personal-porter"
export SERVICE_URL="https://YOUR_NEW_RUN_URL.run.app/api/admin/sync_calendar"
export PORTER_API_KEY="YOUR_KEY_FROM_AUTH_ENV"

# Deploy the Cron Job to run every 6 Hours
gcloud scheduler jobs create http mach2-calendar-sync \
  --schedule="0 */6 * * *" \
  --uri="$SERVICE_URL" \
  --http-method=POST \
  --headers="Authorization=Bearer $PORTER_API_KEY" \
  --location="us-central1" \
  --project="$PROJECT_ID"
```

## 3. Log Diagnostics
You can monitor the automated pulls directly by checking the Cloud Run Logs or Cloud Scheduler Logs on the GCP Console. If you see failures checking for `token.pickle`, ensure your `.auth` directory is securely mounted so the Google SDK can use your refresh token on-demand!
