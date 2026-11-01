"""scale-fn — the /score logic of scale-api as a one-file Cloud Run function (2nd gen, Python 3.11, functions-framework).
Returns the same JSON as the service's /score: score, n, ms, instance, version, revision, cold_start, uptime_s."""
import math, os, time, uuid, threading
import functions_framework
from flask import jsonify

INSTANCE = uuid.uuid4().hex[:8]          # new on every container start
STARTED = time.time()
VERSION = os.environ.get("APP_VERSION", "fn-v1")
_lock = threading.Lock()
_state = {"requests": 0}

def _meta(cold):
    return {"instance": INSTANCE, "version": VERSION, "revision": os.environ.get("K_REVISION", "local"),
            "cold_start": cold, "uptime_s": round(time.time() - STARTED, 2)}

@functions_framework.http
def score(request):
    n = min(int(request.args.get("n", 200000)), 5_000_000)
    t0 = time.perf_counter()
    acc = 0.0
    for i in range(1, n):                 # CPU-bound on purpose, identical to app/main.py
        acc += math.sqrt(i) / (i + 1)
    with _lock: _state["requests"] += 1; cold = _state["requests"] == 1
    return jsonify(score=round(acc, 3), n=n, ms=round((time.perf_counter() - t0) * 1000, 1), **_meta(cold))
