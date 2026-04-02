#!/bin/bash
set -e

# Default configuration
SERVICE_NAME=${SERVICE_NAME:-"workstation-lite"}
REGION=${REGION:-"us-central1"}
PROJECT_ID=$(gcloud config get-value project)

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No GCP project configured. Run 'gcloud config set project <YOUR_PROJECT_ID>'."
    exit 1
fi

echo "Deploying $SERVICE_NAME to Google Cloud Run in $REGION for project $PROJECT_ID..."

# Deploy directly from source using Cloud Build integration
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --port 8080

echo "✅ Deployment complete!"
