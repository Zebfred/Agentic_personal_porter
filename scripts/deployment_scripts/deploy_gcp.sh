#!/bin/bash
# GCP Quick Deploy via Cloud Run using Secret Manager Pipeline

set -euo pipefail

ENV_FILE=".auth/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE missing."
    exit 1
fi

PROJECT_ID=$(grep -v '^#' "$ENV_FILE" | grep -e "GCP_PROJECT_ID" | cut -d '=' -f2 | tr -d '"' | tr -d "'")

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: GCP_PROJECT_ID is missing from $ENV_FILE."
    exit 1
fi

echo "Enabling necessary Google Cloud APIs..."
gcloud services enable run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    --project "$PROJECT_ID"

echo "Fetching Project Number for IAM Secret policies..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting Secret Accessor role to default compute account: $COMPUTE_SA"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None >/dev/null 2>&1 || echo "Warning: IAM update failed/skipped - you may need 'Project IAM Admin' rights."

echo "Building Dynamic Secret Flags from .env hierarchy..."
SECRET_FLAG=""
REMOVE_ENV_FLAG=""
while IFS='=' read -r key _; do
    key=$(echo "$key" | xargs)
    if [ ! -z "$key" ]; then
        if [ -n "$SECRET_FLAG" ]; then
            SECRET_FLAG="${SECRET_FLAG},${key}=${key}:latest"
            REMOVE_ENV_FLAG="${REMOVE_ENV_FLAG},${key}"
        else
            SECRET_FLAG="${key}=${key}:latest"
            REMOVE_ENV_FLAG="${key}"
        fi
    fi
done < <(grep -v '^#' "$ENV_FILE" | grep -v '^\s*$')

echo "Deploying Agentic Personal Porter to Cloud Run natively mapped to GCP Secrets..."
gcloud run deploy agentic-porter \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 5090 \
  --memory 1024Mi \
  --remove-env-vars="${REMOVE_ENV_FLAG}" \
  --set-secrets="${SECRET_FLAG}" \
  --project="${PROJECT_ID}" \
  --quiet

echo "--------------------------------------------------------"
echo "✅ Secure Deployment mapping secrets via GCP completed."
