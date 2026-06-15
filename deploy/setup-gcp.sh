#!/bin/bash
# ============================================================
# EcoTrack — One-shot GCP setup (gcloud only, no Terraform)
# 100% Google services — Vertex AI Gemini as AI provider
# Usage: ./deploy/setup-gcp.sh YOUR_GCP_PROJECT_ID
# ============================================================
set -euo pipefail

PROJECT_ID="${1:?ERROR: ./deploy/setup-gcp.sh YOUR_PROJECT_ID}"
REGION="asia-south1"
SA_NAME="ecotrack-cloudrun"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/ecotrack/app"

echo "🌱 ============================================"
echo "   EcoTrack — 100% Google Cloud Deployment"
echo "   AI: Vertex AI Gemini (no Anthropic)"
echo "   Project: $PROJECT_ID | Region: $REGION"
echo "============================================"

# 1. Set project
gcloud config set project "$PROJECT_ID"

# 2. Enable all 10 GCP APIs
echo "📡 Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  cloudscheduler.googleapis.com \
  aiplatform.googleapis.com \
  cloudtrace.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  secretmanager.googleapis.com
echo "   ✅ 10 APIs enabled"

# 3. Artifact Registry
echo "📦 Creating Artifact Registry..."
gcloud artifacts repositories create ecotrack \
  --repository-format=docker \
  --location="$REGION" \
  --description="EcoTrack Docker images" 2>/dev/null \
  || echo "   (exists, skipping)"

# 4. Firestore
echo "🗄️  Creating Firestore database..."
gcloud firestore databases create \
  --location="$REGION" \
  --type=firestore-native 2>/dev/null \
  || echo "   (exists, skipping)"

# 5. Service Account + IAM roles
echo "🔐 Creating service account..."
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="EcoTrack Cloud Run SA" 2>/dev/null \
  || echo "   (exists, skipping)"

echo "   Assigning IAM roles..."
ROLES=(
  "roles/datastore.user"
  "roles/aiplatform.user"
  "roles/cloudtrace.agent"
  "roles/logging.logWriter"
  "roles/monitoring.metricWriter"
  "roles/secretmanager.secretAccessor"
)
for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$ROLE" --quiet
  echo "   ✅ $ROLE"
done

# 6. Cloud Build permissions
echo "🔧 Setting Cloud Build permissions..."
CB_SA="$(gcloud projects describe $PROJECT_ID \
  --format='value(projectNumber)')@cloudbuild.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CB_SA" \
  --role="roles/run.admin" --quiet
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CB_SA" \
  --role="roles/iam.serviceAccountUser" --quiet
echo "   ✅ Cloud Build permissions set"

# 7. Build and push image
echo "🐳 Building Docker image..."
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
docker build -t "$IMAGE:latest" .
docker push "$IMAGE:latest"
echo "   ✅ Image pushed"

# 8. Deploy to Cloud Run
# NOTE: No API keys needed — Vertex AI auth via service account IAM
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ecotrack \
  --image="$IMAGE:latest" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --timeout=300 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,FIRESTORE_COLLECTION=footprints" \
  --service-account="$SA_EMAIL"

# 9. Cloud Scheduler — weekly analytics
echo "⏰ Creating Cloud Scheduler job..."
SERVICE_URL=$(gcloud run services describe ecotrack \
  --region="$REGION" --format='value(status.url)')

gcloud scheduler jobs create http ecotrack-weekly-aggregate \
  --location="$REGION" \
  --schedule="0 18 * * 0" \
  --time-zone="Asia/Kolkata" \
  --uri="$SERVICE_URL/api/admin/aggregate-stats" \
  --http-method=POST \
  --headers="Content-Type=application/json,X-CloudScheduler-JobName=ecotrack-weekly-aggregate" \
  --message-body="{}" \
  --oidc-service-account-email="$SA_EMAIL" 2>/dev/null \
  || echo "   (exists, skipping)"

# 10. Cloud Monitoring alert
echo "📊 Creating uptime check..."
gcloud monitoring uptime create \
  --display-name="EcoTrack Health" \
  --resource-type="uptime-url" \
  --resource-labels="host=$(echo $SERVICE_URL | sed 's|https://||'),project_id=$PROJECT_ID" \
  --protocol=HTTPS \
  --path="/api/health" \
  --period=300 2>/dev/null || echo "   (skipping — configure in Console)"

echo ""
echo "🎉 ============================================"
echo "   DEPLOYMENT COMPLETE — 100% Google Cloud"
echo "============================================"
echo "🌐 App URL:      $SERVICE_URL"
echo "🏥 Health:       $SERVICE_URL/api/health"
echo "🤖 AI Provider:  Google Vertex AI Gemini"
echo ""
echo "GCP Services Active:"
echo "  ✅ Cloud Run          — App hosting"
echo "  ✅ Artifact Registry  — Docker images"
echo "  ✅ Cloud Build        — CI/CD"
echo "  ✅ Firestore          — User data"
echo "  ✅ Vertex AI Gemini   — AI chat (PRIMARY)"
echo "  ✅ Cloud Logging      — Structured logs"
echo "  ✅ Cloud Monitoring   — Metrics & uptime"
echo "  ✅ Cloud Trace        — Request tracing"
echo "  ✅ Cloud Scheduler    — Weekly cron"
echo "  ✅ Secret Manager     — (available if needed)"
echo ""
echo "⚡ CI/CD: Connect GitHub in Console → Cloud Build → Triggers"
echo "   Build config: cloudbuild.yaml | Branch: ^main$"
