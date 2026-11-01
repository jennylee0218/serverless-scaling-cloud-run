#!/usr/bin/env python3
"""load.py — a tiny load generator (stdlib only). Reports p50/p95, distinct instances and cold starts, and writes results/<label>.json.
  python3 load.py $URL -c 50 -s 60 -l run1
  python3 load.py $URL -c 50 -s 60 -l run2 --setting "concurrency=1"
  python3 load.py $URL --path /count -c 3 -n 20 -l counts     # 3 parallel clients so several instances answer"""
import argparse, json, os, statistics, threading, time, urllib.request
from collections import Counter

ap = argparse.ArgumentParser()
ap.add_argument("url"); ap.add_argument("-c", "--concurrency", type=int, default=50); ap.add_argument("-s", "--seconds", type=int, default=60)
ap.add_argument("-n", "--requests", type=int, default=0, help="stop after N requests instead of after --seconds")
ap.add_argument("-l", "--label", default="run"); ap.add_argument("--path", default="/score?n=200000"); ap.add_argument("--setting", default="")
a = ap.parse_args()

lat, inst, cold, versions, errors = [], Counter(), 0, Counter(), 0
lock = threading.Lock(); stop = time.time() + a.seconds; done = 0; first_ms = None

def worker():
    global cold, errors, done, first_ms
    while True:
        with lock:
            if (a.requests and done >= a.requests) or (not a.requests and time.time() > stop): return
            done += 1
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(a.url.rstrip("/") + a.path, timeout=60) as r:
                body = json.loads(r.read().decode())
            ms = (time.perf_counter() - t0) * 1000
            with lock:
                lat.append(ms); inst[body.get("instance", "?")] += 1; versions[body.get("version", "?")] += 1
                if body.get("cold_start"): cold += 1
                if first_ms is None: first_ms = ms
                if a.path.startswith("/count"): print(f"  {body.get('instance')}  count={body.get('count')}")
        except Exception as e:
            with lock: errors += 1

threads = [threading.Thread(target=worker, daemon=True) for _ in range(a.concurrency)]
t_start = time.time(); [t.start() for t in threads]; [t.join() for t in threads]
elapsed = time.time() - t_start
if not lat: raise SystemExit("no successful requests — is the URL right?")
lat.sort(); p = lambda q: lat[min(len(lat) - 1, int(q * len(lat)))]
res = {"label": a.label, "setting": a.setting, "path": a.path, "concurrency_clients": a.concurrency, "seconds": round(elapsed, 1),
       "requests": len(lat), "errors": errors, "rps": round(len(lat) / elapsed, 1), "first_request_ms": round(first_ms, 1),
       "p50_ms": round(p(0.50), 1), "p95_ms": round(p(0.95), 1), "max_ms": round(lat[-1], 1),
       "distinct_instances": len(inst), "cold_starts": cold, "requests_per_instance": dict(inst.most_common()), "versions": dict(versions),
       "finished_at": time.strftime("%Y-%m-%d %H:%M:%S")}
os.makedirs("results", exist_ok=True)
with open(f"results/{a.label}.json", "w") as f: json.dump(res, f, indent=2)
print(f"\n{a.label}  {a.setting}\n  requests {res['requests']}  errors {errors}  rps {res['rps']}\n  first {res['first_request_ms']} ms   p50 {res['p50_ms']} ms   p95 {res['p95_ms']} ms   max {res['max_ms']} ms"
      f"\n  distinct instances {res['distinct_instances']}   cold starts {cold}   versions {dict(versions)}\n  → results/{a.label}.json")
