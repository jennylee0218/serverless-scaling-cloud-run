#!/usr/bin/env bash
# Part 6 — yours, not the agent's. Deletes the Cloud Run service, the Cloud Run function and their images/sources.
# Assignment 3 additions: the function (scale-fn), its gcf-artifacts image repo and its gcf-v2-* source buckets.
# Dataproc line dropped: Assignment 3 never creates a cluster (setup.sh was not run).
set -uo pipefail
source ./env.sh
gcloud run services delete "$SERVICE" --region "$REGION" --quiet
gcloud functions delete scale-fn --gen2 --region "$REGION" --quiet
gcloud artifacts repositories delete cloud-run-source-deploy --location "$REGION" --quiet 2>/dev/null || true
gcloud artifacts repositories delete gcf-artifacts --location "$REGION" --quiet 2>/dev/null || true
PN=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
for b in "gcf-v2-sources-$PN-$REGION" "gcf-v2-uploads-$PN.$REGION.cloudfunctions.appspot.com"; do
  gcloud storage rm --recursive "gs://$b" --quiet 2>/dev/null || true
done
date +"%F %T  cleanup done (service, function, images, function sources)" | tee -a timestamps.txt
echo "Left running:"; gcloud run services list --region "$REGION"; gcloud functions list --regions "$REGION"
echo "Check tomorrow: console → Billing → Reports should show today's spend flat."
