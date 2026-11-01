#!/usr/bin/env bash
# Parts 3–4 — the knobs, one at a time. Each prints the command it runs so it lands in your notes.
#   ./knobs.sh conc 1            per-instance concurrency (80 default)
#   ./knobs.sh min 1             min-instances (0 default) — removes the cold start, bills while idle
#   ./knobs.sh cpu 2             vCPU per instance
#   ./knobs.sh canary 10         send 10% of traffic to the latest revision (after ./deploy.sh v2 --no-traffic)
#   ./knobs.sh rollback          100% back to the previous revision (the one that was serving before v2)
#   ./knobs.sh describe          save the service description to results/svc.yaml (for Claude)
set -euo pipefail
source ./env.sh
case "${1:-}" in
  conc)     set -x; gcloud run services update "$SERVICE" --region "$REGION" --concurrency "$2" ;;
  min)      set -x; gcloud run services update "$SERVICE" --region "$REGION" --min-instances "$2" ;;
  cpu)      set -x; gcloud run services update "$SERVICE" --region "$REGION" --cpu "$2" ;;
  canary)   set -x; gcloud run services update-traffic "$SERVICE" --region "$REGION" --to-revisions "LATEST=$2" ;;
  rollback) PREV=$(gcloud run revisions list --service "$SERVICE" --region "$REGION" --format='value(name)' --sort-by=~creationTimestamp | sed -n 2p)
            set -x; gcloud run services update-traffic "$SERVICE" --region "$REGION" --to-revisions "$PREV=100" ;;
  describe) mkdir -p results; gcloud run services describe "$SERVICE" --region "$REGION" --format yaml > results/svc.yaml; echo "results/svc.yaml written" ;;
  *) echo "usage: ./knobs.sh conc N | min N | cpu N | canary PCT | rollback | describe"; exit 1 ;;
esac
