#!/usr/bin/env python3
"""Part 3 second source — Cloud Monitoring numbers for each load.py run window (results/run_windows.txt).
Each knobs.sh update creates a new revision, so every run is matched to the revision that was serving when it started
and only that revision's series are read (otherwise the previous run's instances bleed into the next window, because the
instance-count gauge lags about a minute). For every run: peak container instance count (max per minute, active and
active+idle) from run start to 2 min after run end, and server-side p50/p95 request latency over the run window. Writes results/monitoring.json (numbers only; no
project id). The access token stays in memory.
  python3 monitoring_check.py            # all runs in results/run_windows.txt"""
import json, subprocess, urllib.parse, urllib.request, datetime as dt

PROJECT = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True).stdout.strip()
TOKEN = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip()
REGION = subprocess.run(["gcloud", "config", "get-value", "run/region"], capture_output=True, text=True).stdout.strip()
SERVICE_FOR = {"run5": "scale-fn"}                     # every other run hits scale-api

def ts_list(filt, start, end, **agg):
    q = [("filter", filt), ("interval.startTime", start), ("interval.endTime", end)] + [(f"aggregation.{k}", v) for k, v in agg.items()]
    url = f"https://monitoring.googleapis.com/v3/projects/{PROJECT}/timeSeries?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    return json.load(urllib.request.urlopen(req)).get("timeSeries", [])

def revision_for(svc, start):
    revs = subprocess.run(["gcloud", "run", "revisions", "list", "--service", svc, "--region", REGION,
                           "--format=value(metadata.name,metadata.creationTimestamp)"], capture_output=True, text=True).stdout.split("\n")
    best = None
    for line in filter(None, revs):
        name, created = line.split()
        c = dt.datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
        if c <= start and (best is None or c > best[1]): best = (name, c)
    return best[0]

def val(p):
    v = p["value"]; return float(v.get("doubleValue", v.get("int64Value", 0)))

def iso(t): return t.strftime("%Y-%m-%dT%H:%M:%SZ")

windows = {}
for line in open("results/run_windows.txt"):
    run, what, t = line.split()
    windows.setdefault(run, {})[what] = dt.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ")

out = {}
for run, w in windows.items():
    if "end" not in w: continue
    svc = SERVICE_FOR.get(run, "scale-api")
    rev = revision_for(svc, w["start"])
    base = f'resource.type="cloud_run_revision" AND resource.labels.service_name="{svc}" AND resource.labels.revision_name="{rev}"'
    # instance count: per-minute gauge, read until 2 min after the run because it lags; this revision only
    s, e = iso(w["start"]), iso(w["end"] + dt.timedelta(minutes=2))
    inst = {}
    for state in ("active", "idle"):
        series = ts_list(base + f' AND metric.type="run.googleapis.com/container/instance_count" AND metric.labels.state="{state}"',
                         s, e, alignmentPeriod="60s", perSeriesAligner="ALIGN_MAX", crossSeriesReducer="REDUCE_SUM")
        pts = series[0]["points"] if series else []
        inst[state] = [val(p) for p in reversed(pts)]
    per_min_total = [a + b for a, b in zip(inst["active"], inst["idle"])] if inst["idle"] else inst["active"]
    # latency: one alignment bucket covering exactly the run window → a single server-side p50 / p95 for the run
    secs = int((w["end"] - w["start"]).total_seconds()) + 1
    lat = {}
    for name, aligner in (("p50", "ALIGN_PERCENTILE_50"), ("p95", "ALIGN_PERCENTILE_95")):
        series = ts_list(base + ' AND metric.type="run.googleapis.com/request_latencies" AND metric.labels.response_code_class="2xx"', iso(w["start"]), iso(w["end"]),
                         alignmentPeriod=f"{secs}s", perSeriesAligner=aligner, crossSeriesReducer="REDUCE_MAX")
        pts = [val(p) for sr in series for p in sr["points"]]
        lat[name] = round(max(pts), 1) if pts else None
    out[run] = {"service": svc, "revision": rev, "window_utc": [iso(w["start"]), iso(w["end"])],
                "instances_active_per_min": inst["active"], "instances_idle_per_min": inst["idle"],
                "peak_instances_active": max(inst["active"], default=None), "peak_instances_total": max(per_min_total, default=None),
                "server_p50_ms": lat["p50"], "server_p95_ms": lat["p95"]}
    print(f"{run:5} {rev:20} peak active {out[run]['peak_instances_active']}  peak total {out[run]['peak_instances_total']}"
          f"  server p50 {lat['p50']} ms  p95 {lat['p95']} ms")

json.dump(out, open("results/monitoring.json", "w"), indent=2)
print("→ results/monitoring.json")
