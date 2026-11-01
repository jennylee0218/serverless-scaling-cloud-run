#!/usr/bin/env bash
# Part 2 — the brief's five runs, verbatim, with a 90 s gap between them so 1-minute Metrics buckets don't overlap.
# Logs each run's UTC window to results/run_windows.txt (for matching against Cloud Monitoring) and probes client
# TCP connect time with 30 parallel curls in the gap after run1 (results/connect_probe.txt) to show where load.py's p95 tail comes from.
set -euo pipefail
source ./url.sh; source ./fn_url.sh
win() { echo "$1 $2 $(date -u +%FT%TZ)" | tee -a results/run_windows.txt; }
gap() { echo "gap 90 s"; sleep 90; }
probe() { for i in $(seq 1 30); do curl -s -o /dev/null -w "connect_s=%{time_connect} total_s=%{time_total}\n" "$URL/score?n=200000" & done; wait; } 

win run1 start; python3 load.py $URL -c 50 -s 60 -l run1 --setting concurrency=80; win run1 end; sleep 15; probe > results/connect_probe.txt; gap
./knobs.sh conc 1; win run2 start; python3 load.py $URL -c 50 -s 60 -l run2 --setting concurrency=1; win run2 end; gap
./knobs.sh min 1;  win run3 start; python3 load.py $URL -c 50 -s 60 -l run3 --setting "concurrency=1,min=1"; win run3 end; gap
./knobs.sh cpu 2;  win run4 start; python3 load.py $URL -c 50 -s 60 -l run4 --setting "concurrency=1,min=1,cpu=2"; win run4 end; gap
win run5 start; python3 load.py $FUNCTION_URL -c 50 -s 60 -l run5 --setting function; win run5 end
date +"%F %T  runs 1-5 done" | tee -a timestamps.txt
