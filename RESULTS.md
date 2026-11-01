# Assignment 3 — results sheet (this file is the submission; every cell is a number or one sentence)

Name: Jenny Lee   CNET ID: jennylee0218   Project region: us-central1

## Part 1 — Deploy twice
| deployment | URL (no project id needed) | cold ms | warm ms | instance id |
|---|---|---|---|---|
| Cloud Run service (your Dockerfile) | https://scale-api-<hash>-uc.a.run.app | 3928 | 95 | ff01fed5 (same both calls) |
| Cloud Run function (2nd gen) | https://scale-fn-<hash>-uc.a.run.app | 779 (after 17 min idle; the first curl right after deploy was 169 ms because the deploy had pre-started that instance, uptime_s 19.86) | 97 | ad55b1f1 (same both calls) |

What you changed in your Dockerfile (one line): Non-root `appuser` with `COPY --chown` (the kit's files are mode 700, so my first deploy returned 503 with PermissionError on main.py), exec-form gunicorn with `--timeout 0`, pip cache off and a `.dockerignore`; kept 1 worker × 8 threads so the runs stay comparable.
Both answers for `/score?n=200000` — paste the two JSON `score` values: service 891.11 · function 891.11 · same? yes — identical loop on Python 3.11 in both.

| service `/score?n=200000` | function `?n=200000` |
|---|---|
| `{"cold_start":true,"instance":"ff01fed5","ms":37.8,"n":200000,"revision":"scale-api-00002-p7f","score":891.11,"uptime_s":0.06,"version":"v1"}` | `{"cold_start":true,"instance":"ad55b1f1","ms":33.1,"n":200000,"revision":"scale-fn-00001-qay","score":891.11,"uptime_s":0.13,"version":"fn-v1"}` |

Commands: `./deploy.sh` · `./function/deploy_function.sh` (gcloud functions deploy scale-fn --gen2 --runtime python311 --trigger-http --memory 512Mi --cpu 1 --concurrency 1 --max-instances 50) · `./run_loads.sh` (the five runs below, verbatim, 90 s apart) · `python3 monitoring_check.py`.

## Part 2 — Five runs (50 clients, 60 s)
| run | setting | requests | errors | first ms | p50 ms | p95 ms | distinct instances | cold starts |
|---|---|---|---|---|---|---|---|---|
| run1 | concurrency=80 | 1870 | 1 | 1505.3 | 1529.7 | 3336.2 | 3 | 3 |
| run2 | concurrency=1 | 5522 | 13 | 512.4 | 56.0 | 5054.1 | 37 | 37 |
| run3 | concurrency=1,min=1 | 5824 | 5 | 1897.3 | 58.2 | 5055.6 | 25 | 25 |
| run4 | concurrency=1,min=1,cpu=2 | 7002 | 7 | 1218.1 | 59.6 | 5046.3 | 22 | 22 |
| run5 | function | 5659 | 10 | 735.6 | 68.7 | 5069.2 | 23 | 22 (one instance had already served my Part 1 curls) |

Screenshots attached: Metrics → Container instance count screenshots/metrics_instance_count.png · Metrics → Request latency screenshots/metrics_request_latency.png (taken 10:19 PM CT; runs 1–4 = 10:07–10:18 PM CT, revision markers at each knob change)

## Part 3 — Validate the numbers (load.py says · second source says · match?)
Second source = Cloud Monitoring (the same data as the Metrics tab), read per revision for each run's window (results/monitoring.json, results/run_windows.txt).

| check | load.py says | second source says | match? (yes / no + why) |
|---|---|---|---|
| 1 Instances, run1 vs run2 (peak of the Metrics chart) | run1 3 / run2 37 | run1 3 / run2 48 (Cloud Run logs: 3 instance starts during run1, 49 on run2's revision; the console chart's 1-minute view shows ~2 for run1) | yes for the shape (run2 is 12–16× run1); run2's extra 11–12 are instances Cloud Run started for the opening 50-request burst that never returned a successful answer to load.py, which only counts instances that answered. |
| 2 p95, run1 and run2 (Metrics p95, same window) | run1 3336 / run2 5054 | run1 3124 / run2 50 | run1 yes (7% apart: queueing at concurrency 80 shows on both sides); run2 no — the 5 s is client-side TCP connect stalls in Cloud Shell (10 of 30 parallel curls took 5–20 s to connect, results/connect_probe.txt), which server-side latency never sees. |
| 3 Cold starts = new instances (run2); first ms run3 vs run2 | cold 37 inst 37 ; first run2 512 run3 1897 | Cloud Run logs: 49 instance starts on run2's revision; one MANUAL_OR_CUSTOMER_MIN_INSTANCE start 8 s before run3; earliest server latency run2 438 ms, run3 52 ms | cold = instances yes for what load.py can see (the app flags each instance's first request, so even a pre-warmed instance counts once), though Cloud Run started 49, so 12 paid a cold start without answering load.py; first ms no — load.py's run3 first is 1385 ms higher because it times the first request to complete including the client connect stalls, while server-side min=1 cut the first answer by ~386 ms (438 → 52 ms). |
| 4 Going high: run4 vs run3 (p95, instances) | run3 5056/25 run4 5046/22 | — (Monitoring: server p95 98 → 97 ms, peak 27 → 27) | verdict for this service: high or wide? wide — cpu 2 moved p95 by under 1% (and p50 58 → 60 ms) because one gunicorn worker runs one single-threaded Python request per instance on one core, so the second vCPU only doubled the vCPU price. |
| 5 Function vs service: run5 vs run2 (instances, p95) | run2 37/5054 run5 23/5069 | — (Monitoring: peak 48 vs 22, server p95 50 vs 65 ms) | one line: Same code and size (512Mi, 1 vCPU, concurrency 1, max 50), but the function is ~10 ms slower server-side (p50 39 → 49 ms), most likely functions-framework's request wrapper, and needed fewer instances for the same traffic (unverified why); both client p95s are the same Cloud Shell connect stall. |
| 6 Cost, run1: /scale-report · your pricing-page arithmetic · next day's Billing report | $ 0.0730 (run2–6: 0.0100 / 0.0109 / 0.0234 / 0.0121 / 0.0345) | $ 0.0037 · $ 0.67 for the day before credits ($0.00 after my credits) | no — scale-report bills requests × p50 = 2861 s as if every request had its own instance, but at concurrency 80 the requests overlapped on 3 instances that billed 118.6 instance-s (Monitoring billable_instance_time): 118.6 × ($0.000024 vCPU-s + 0.5 GiB × $0.0000025 GiB-s) + 1870 × $0.40/M = $0.0037, ~20× lower (an upper bound: it includes the 30-curl connect probe in the gap after run1); Billing's $0.67 is not comparable to either, because it covers the whole session (Part 1 deploys, all six runs, the idle min=1 instance, Part 4) and not only run1's 70 s, and my prediction of ~$0.00 from the free tier was wrong before credits; it is still under the brief's $1. |

## Part 4 — Claude, controlled
| | knob proposed | predicted p95 | predicted instances | measured p95 (run6) | measured instances (run6) | held? |
|---|---|---|---|---|---|---|
| Claude Code | concurrency 1 → 4 (keep min 1, cpu 2) | server ~150 ms (100–250); load.py ~5.05 s; cost ~$0.017 | ~12 (8–16) | server 237.5 ms; load.py 5106 ms; cost $0.0114 | 17 (Metrics peak 19) | partly: p95 inside the range but 58% above its point estimate, load.py p95 held, instances missed (17 > 16), cost lower than predicted (192.5 billable instance-s × ($0.000048 + $0.00000125) + 4909 × $0.40/M) |

`grep -i delete .claude/tool-log.txt` is empty: yes (5 entries, 0 matches)   · what settings.json allowed / denied (one sentence): It allowed Read/Glob/Grep, `python3`, `cat`, `ls`, `jq` and read-only `gcloud … describe/list`, denied every delete (Cloud Run service, Dataproc cluster, project, Artifact Registry repo), `rm -rf`, `./cleanup.sh` and reading `env.sh`/`url.sh`, and anything else (such as `./knobs.sh`) needed my approval.

Note: the knob change (`./knobs.sh conc 4`) was made in a Claude session started from my home folder, so the hook did not log it (prompts.md row 2 records it); the tool log is from the session re-launched from this folder, which ran `./knobs.sh describe` and the scale-report script (prompts.md row 3).

## Cost discipline
timestamps.txt lines (create → delete) pasted here:
```
2026-10-19 02:58:27  APIs enabled (run, cloudbuild, artifactregistry, cloudfunctions, monitoring) — no setup.sh, no Dataproc
2026-10-19 02:59:40  deploy v1
2026-10-19 03:01:02  deploy v1
2026-10-19 03:06:31  deploy function scale-fn
2026-10-19 03:20:21  runs 1-5 done
2026-10-19 03:51:11  cleanup done (service, function, images, function sources)
2026-10-19 03:52:16  removed leftover function upload bucket (gcf-v2-uploads); verified: 0 services, 0 functions, 0 image repos, 0 clusters
```
The second `deploy v1` is the redeploy after the 503 fix. Cleanup was run from the terminal, outside the hooked Claude session, so tool-log.txt stays clean.
