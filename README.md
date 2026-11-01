# Serverless scaling on Google Cloud Run: service vs function

The same CPU-bound endpoint deployed two ways: as a **Cloud Run service** from my own Dockerfile and as a
**Cloud Run function (2nd gen)**. I load-tested both at 50 concurrent clients and changed one scaling setting per run.
Then I checked every load-generator number against **Cloud Monitoring** as an independent second source.

Full results sheet: **[RESULTS.md](RESULTS.md)**

## What I built
- **[app/Dockerfile](app/Dockerfile)**: runs as a non-root user (`COPY --chown`, which fixed a 503 caused by mode-700
  files), exec-form gunicorn as PID 1 so it gets SIGTERM, `--timeout 0`, layer-cached dependencies, `.dockerignore`.
- **[function/](function/)**: the `/score` logic ported to `functions-framework`, returning the same JSON, plus its deploy script.
- **[run_loads.sh](run_loads.sh)**: five runs with 90 s gaps so 1-minute metric buckets don't overlap. It logs each
  run's UTC window and probes client TCP connect times.
- **[monitoring_check.py](monitoring_check.py)**: pulls instance counts and server-side p50/p95 for each run from the
  Cloud Monitoring API. It matches each run to the revision that was serving at the time, because the gauge lags about a minute.
- **[cleanup.sh](cleanup.sh)**: tears down the service, the function, the image repos and the function source buckets.
  Everything was verified deleted at the end.

## Results (50 clients, 60 s each)
| run | setting | requests | p50 | p95 (client) | instances |
|---|---|---|---|---|---|
| 1 | concurrency 80 | 1,870 | 1,530 ms | 3,336 ms | 3 |
| 2 | concurrency 1 | 5,522 | 56 ms | 5,054 ms | 37 |
| 3 | + min instances 1 | 5,824 | 58 ms | 5,056 ms | 25 |
| 4 | + 2 vCPU | 7,002 | 60 ms | 5,046 ms | 22 |
| 5 | Cloud Run function | 5,659 | 69 ms | 5,069 ms | 23 |

What the second source showed:
- **The 5 s p95 was not the server.** Server-side p95 for run 2 was **50 ms**. The tail was TCP connect stalls in
  Cloud Shell: 10 of 30 parallel curls took 5–20 s just to connect.
- **Scale wide, not high, for this service.** 2 vCPUs moved p95 by under 1 %, because one gunicorn worker runs one
  single-threaded Python request per instance. The second vCPU only doubled the price.
- **The built-in cost estimate was about 20× too high** for run 1. It billed requests × p50 as if every request had its
  own instance. Billable instance-seconds from Monitoring gave $0.0037.
- Cloud Run started **49** instances in run 2, but the client only saw 37. The other 12 were started for the opening burst and never answered.

## Layout
```
app/             Flask service + my Dockerfile
function/        the same endpoint as a Cloud Run function
load.py          stdlib load generator (p50/p95, distinct instances, cold starts)
run_loads.sh     the five runs  ·  knobs.sh  change one scaling setting  ·  deploy.sh / cleanup.sh
monitoring_check.py   Cloud Monitoring cross-check
results/         raw JSON for every run, monitoring data, connect probe, cost report
screenshots/     Metrics: container instance count and request latency
```

## Run it
Needs a GCP project with Cloud Run, Cloud Build, Artifact Registry and Cloud Functions enabled.
```bash
./deploy.sh && ./function/deploy_function.sh
./run_loads.sh && python3 monitoring_check.py
./cleanup.sh
```

## Stack
Google Cloud Run · Cloud Run functions (2nd gen) · Docker · gunicorn · Flask · Cloud Monitoring API · Python

---
Course work for *ADSP 32030 Scalable Data Systems*, University of Chicago (Fall 2026).
`app/main.py`, `load.py`, `deploy.sh` and `knobs.sh` were provided by the course. The Dockerfile, function, load and
monitoring scripts, cleanup changes and analysis are mine.
