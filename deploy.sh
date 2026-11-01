#!/usr/bin/env bash
# Part 2 — deploy scale-api to Cloud Run from source: Cloud Build builds app/Dockerfile for you (without a Dockerfile it would use a buildpack).
#   ./deploy.sh                 v1, concurrency 80, min-instances 0, 1 vCPU
#   ./deploy.sh v2 --no-traffic a second revision that receives no traffic until you split it (Part 4)
set -euo pipefail
source ./env.sh
VERSION="${1:-v1}"; shift || true
gcloud run deploy "$SERVICE" --source ./app --region "$REGION" --allow-unauthenticated \
  --concurrency 80 --min-instances 0 --max-instances 50 --cpu 1 --memory 512Mi \
  --set-env-vars "APP_VERSION=$VERSION" "$@"
URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
echo "export URL=$URL" > url.sh
date +"%F %T  deploy $VERSION" | tee -a timestamps.txt
echo "URL=$URL   (source url.sh to set \$URL)"
