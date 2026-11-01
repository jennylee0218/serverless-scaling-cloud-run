#!/usr/bin/env bash
# Part 1.2 — deploy the /score logic as a Cloud Run function (2nd gen), sized to match run2's service settings.
set -euo pipefail
source ./env.sh
gcloud functions deploy scale-fn --gen2 --runtime python311 --region "$REGION" --source ./function \
  --entry-point score --trigger-http --allow-unauthenticated \
  --memory 512Mi --cpu 1 --concurrency 1 --max-instances 50
FUNCTION_URL=$(gcloud functions describe scale-fn --gen2 --region "$REGION" --format='value(serviceConfig.uri)')
echo "export FUNCTION_URL=$FUNCTION_URL" > fn_url.sh
date +"%F %T  deploy function scale-fn" | tee -a timestamps.txt
echo "FUNCTION_URL=$FUNCTION_URL   (source fn_url.sh)"
