#!/bin/bash
set -euo pipefail

# ============================================================================
# sync_gcp_secrets.sh
# 
# Purpose: Automatically reads the .auth/.env file and syncs all key-value pairs 
#          to Google Cloud Secret Manager. It will create the secret container 
#          if it doesn't exist, and add a new version with the current value.
# ============================================================================
# Improvements needed:
#  - Check if current secret value is the same as the one in the .env file, if so, skip.
#  - 
#
# Ensure we are in the project root by resolving the absolute path of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_ROOT}/.auth/.env"

# Edge Case 1: Check if .env file actually exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ Error: .env file not found at $ENV_FILE"
    echo "Please ensure your .env file exists in the project root."
    exit 1
fi

echo "🚀 Starting synchronization of secrets from .env to GCP Secret Manager..."

# Read the .env file line by line
while IFS='=' read -r key value || [ -n "$key" ]; do
    # Edge Case 2: Skip empty lines and comments
    if [[ -z "$key" ]] || [[ "$key" == \#* ]]; then
        continue
    fi
    
    # Trim potential whitespace and surrounding quotes from the value
    clean_value=$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    
    # Edge Case 3: Skip variables that have no value assigned
    if [[ -z "$clean_value" ]]; then
        echo "⚠️  Skipping '$key' because its value is empty."
        continue
    fi

    # Check if the secret container already exists in GCP
    if ! gcloud secrets describe "$key" >/dev/null 2>&1; then
        echo "📦 Creating new secret container in GCP: $key"
        gcloud secrets create "$key" --replication-policy="automatic"
    fi

    # Add the new secret version
    echo "✅ Pushing new version for secret: $key"
    echo -n "$clean_value" | gcloud secrets versions add "$key" --data-file=-

done < "$ENV_FILE"

echo "🎉 All secrets from .env have been successfully synced to Google Cloud Secret Manager!"
