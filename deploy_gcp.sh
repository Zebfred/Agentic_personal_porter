#!/bin/bash
# GCP Quick Deploy via Cloud Run

echo "Enabling necessary Google Cloud APIs..."
gcloud services enable run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project long-facet-473520-n0

echo "Extracting Database credentials from .auth/.env..."
# Read directly from the auth file
source <(grep -v '^#' .auth/.env | sed 's/ = /=/g')

echo "Deploying Agentic Personal Porter to Cloud Run..."
gcloud run deploy agentic-porter \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 5090 \
  --memory 1024Mi \
  --set-env-vars="GROQ_API_KEY=${GROQ_API_KEY},MONGO_URI=${MONGO_URI},NEO4J_URI=${NEO4J_URI},NEO4J_USERNAME=${NEO4J_USERNAME},NEO4J_PASSWORD=${NEO4J_PASSWORD},PORTER_API_KEY=${PORTER_API_KEY},JWT_SECRET=${JWT_SECRET}" \
  --project="long-facet-473520-n0" \
  --quiet

echo "Deployment attempt completed!"
