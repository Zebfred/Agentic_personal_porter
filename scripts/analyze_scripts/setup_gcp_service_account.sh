#!/bin/bash
set -euo pipefail

# =====================================================================
# GCP Service Account Provisioning
#
# Creates the porter-compute-sa service account and binds the
# Compute Instance Admin (v1) role. Uses Application Default
# Credentials (ADC) via `gcloud auth application-default login`
# instead of downloading a JSON key file.
# =====================================================================

# Source project ID from .auth/.env — NEVER hardcode GCP project IDs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.auth/.env"

if [ -f "$ENV_FILE" ]; then
    PROJECT_ID=$(grep -v '^#' "$ENV_FILE" | grep 'GCP_PROJECT_ID' | cut -d '=' -f2 | tr -d '"' | tr -d "'" | xargs)
fi

if [ -z "${PROJECT_ID:-}" ]; then
    echo "❌ ERROR: GCP_PROJECT_ID is not set. Add it to .auth/.env"
    exit 1
fi

SA_NAME="porter-compute-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=========================================================="
echo "🛡️ PROVISIONING GCP SERVICE ACCOUNT: ${SA_NAME}"
echo "=========================================================="

echo "[1/2] Creating Service Account: $SA_EMAIL"
gcloud iam service-accounts create $SA_NAME \
    --description="Dedicated Service Account for Agentic Porter local compute management" \
    --display-name="Agentic Porter Compute SA" \
    --project=$PROJECT_ID || echo "Service account may already exist. Skipping creation..."

echo ""
echo "[2/2] Binding Compute Instance Admin (v1) Role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/compute.instanceAdmin.v1" \
    --condition=None

echo "=========================================================="
echo "✅ SUCCESS! Service Account provisioned."
echo ""
echo "For local development, authenticate via ADC:"
echo "  gcloud auth application-default login"
echo ""
echo "For production (Cloud Run), attach this SA to the service."
echo "=========================================================="
