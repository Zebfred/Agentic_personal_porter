#!/bin/bash
set -euo pipefail

echo "========================================================"
echo "    Vertex AI Billing Killswitch Deployment Script      "
echo "========================================================"

# Check for gcloud
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud is not installed. Please install the Google Cloud CLI."
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No GCP project set. Run: gcloud config set project [YOUR_PROJECT_ID]"
    exit 1
fi

echo "Deploying to Project: $PROJECT_ID"

# 1. Enable necessary APIs
echo "Enabling necessary APIs (Cloud Functions, Pub/Sub, Cloud Build, Service Usage)..."
gcloud services enable cloudfunctions.googleapis.com \
                       pubsub.googleapis.com \
                       cloudbuild.googleapis.com \
                       serviceusage.googleapis.com

# 2. Create the Pub/Sub topic
TOPIC_NAME="budget-alerts"
echo "Checking if Pub/Sub topic '$TOPIC_NAME' exists..."
if gcloud pubsub topics list --format="value(name)" | grep -q "$TOPIC_NAME"; then
    echo "Topic '$TOPIC_NAME' already exists."
else
    echo "Creating Pub/Sub topic: $TOPIC_NAME..."
    gcloud pubsub topics create $TOPIC_NAME
fi

# 3. Deploy the Cloud Function
FUNCTION_NAME="stop_billing"
REGION="us-central1"

echo "Deploying Cloud Function '$FUNCTION_NAME'..."
cd "$(dirname "$0")/billing_killswitch"

gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime python311 \
    --trigger-topic $TOPIC_NAME \
    --entry-point stop_billing \
    --region $REGION \
    --set-env-vars GCP_PROJECT=$PROJECT_ID \
    --service-account="${PROJECT_ID}@appspot.gserviceaccount.com"

echo ""
echo "========================================================"
echo "✅ Cloud Function Deployment Complete!"
echo "========================================================"
echo "⚠️  CRITICAL NEXT STEP: You must manually link your Billing Account's Budget to this Pub/Sub Topic."
echo ""
echo "1. Go to the Google Cloud Console: https://console.cloud.google.com/billing"
echo "2. Select 'Budgets & alerts' from the left sidebar."
echo "3. Create a new budget or edit an existing one."
echo "4. In the 'Actions' section at the bottom, check 'Connect a Pub/Sub topic to this budget'."
echo "5. Select the project '$PROJECT_ID' and the topic '$TOPIC_NAME'."
echo "6. Save the budget."
echo ""
echo "Once configured, if your billing hits 100% of the threshold, the Cloud Function will execute"
echo "and instantly disable the 'aiplatform.googleapis.com' (Vertex AI) API."
echo "========================================================"
