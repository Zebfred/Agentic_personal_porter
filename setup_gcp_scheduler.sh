#!/bin/bash
set -euo pipefail

# This script provisions Google Cloud Scheduler jobs to autonomously hit the
# Cloud Run endpoints, securely transmitting the API Key to authorize execution.

# Set up relative .env sourcing
echo "Setting up Cloud Scheduler cron jobs..."
ENV_FILE="./.auth/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE does not exist. Ensure your .auth directory is configured."
    exit 1
fi

# Extract variables from .env
export PORTER_API_KEY=$(grep -v '^#' $ENV_FILE | grep -e "PORTER_API_KEY" | cut -d '=' -f2 | tr -d '"' | tr -d "'")
export GCP_PROJECT_ID=$(grep -v '^#' $ENV_FILE | grep -e "GCP_PROJECT_ID" | cut -d '=' -f2 | tr -d '"' | tr -d "'")
export GCP_RUN_SERVICE_URL=$(grep -v '^#' $ENV_FILE | grep -e "GCP_RUN_SERVICE_URL" | cut -d '=' -f2 | tr -d '"' | tr -d "'")

if [ -z "$PORTER_API_KEY" ] || [ -z "$GCP_PROJECT_ID" ] || [ -z "$GCP_RUN_SERVICE_URL" ]; then
    echo "ERROR: Required variables (PORTER_API_KEY, GCP_PROJECT_ID, GCP_RUN_SERVICE_URL) missing in $ENV_FILE"
    exit 1
fi

echo "Deploying to Project: $GCP_PROJECT_ID"
echo "Targeting Base URL: $GCP_RUN_SERVICE_URL"
echo "--------------------------------------------------------"

# 1. Calendar Pulse Sync (8:00 AM and 10:00 PM)
echo "Deploying Job 1: Calendar Sync Pulse..."
gcloud scheduler jobs create http mach2-calendar-sync \
  --schedule="0 8,22 * * *" \
  --uri="${GCP_RUN_SERVICE_URL}/api/admin/sync_calendar" \
  --http-method=POST \
  --headers="Authorization=Bearer ${PORTER_API_KEY}" \
  --location="us-central1" \
  --project="${GCP_PROJECT_ID}" || echo "Job 1 already exists or failed to update. Use 'update' to override."

echo "--------------------------------------------------------"

# 2. Vector DB Batch Sync (Noon and Midnight)
echo "Deploying Job 2: Vector Database Batch Sync..."
gcloud scheduler jobs create http mach2-vector-sync \
  --schedule="0 0,12 * * *" \
  --uri="${GCP_RUN_SERVICE_URL}/api/admin/vector_sync" \
  --http-method=POST \
  --headers="Authorization=Bearer ${PORTER_API_KEY}" \
  --location="us-central1" \
  --project="${GCP_PROJECT_ID}" || echo "Job 2 already exists or failed to update. Use 'update' to override."

echo "--------------------------------------------------------"
echo "✅ Orchestration Configuration Complete."
echo "You can manually test these jobs by running:"
echo "gcloud scheduler jobs run mach2-calendar-sync --location us-central1 --project $GCP_PROJECT_ID"
