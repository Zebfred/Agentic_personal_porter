#!/bin/bash
# GCP Quick Deploy via Cloud Run

echo "Enabling necessary Google Cloud APIs..."
gcloud services enable run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project long-facet-473520-n0


echo "Deploying Agentic Personal Porter to Cloud Run..."
gcloud run deploy agentic-porter \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 5090 \
  --memory 1024Mi \
  --set-env-vars=$(grep -v '^#' .auth/.env | sed 's/ = /=/g' | paste -sd "," -) \
  --project="long-facet-473520-n0" \
  --quiet

echo "Deployment attempt completed!"
