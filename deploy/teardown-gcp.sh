#!/bin/bash
set -euo pipefail
PROJECT_ID="${1:?Pass project ID}"
REGION="asia-south1"
echo "⚠️  Removing all EcoTrack resources from $PROJECT_ID..."
gcloud run services delete ecotrack --region="$REGION" --quiet 2>/dev/null || true
gcloud scheduler jobs delete ecotrack-weekly-aggregate --location="$REGION" --quiet 2>/dev/null || true
gcloud artifacts repositories delete ecotrack --location="$REGION" --quiet 2>/dev/null || true
gcloud iam service-accounts delete \
  "ecotrack-cloudrun@$PROJECT_ID.iam.gserviceaccount.com" --quiet 2>/dev/null || true
echo "✅ Teardown complete."
