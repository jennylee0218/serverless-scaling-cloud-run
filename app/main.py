"""scale-api — the tiny service for ADSP 32030 Week 3.
/score  burns a little CPU and reports which instance answered and whether this was its first request (cold start).
/count  increments an in-memory counter — deliberately wrong on more than one instance (that is the lesson).
/       hello + version.  Cloud Run sets K_REVISION / K_SERVICE for us."""
import math, os, time, uuid, threading
from flask import Flask, jsonify, request

app = Flask(__name__)
INSTANCE = uuid.uuid4().hex[:8]          # new on every container start
STARTED = time.time()
VERSION = os.environ.get("APP_VERSION", "v1")
_lock = threading.Lock()
_state = {"count": 0, "requests": 0}

def _meta(cold):
    return {"instance": INSTANCE, "version": VERSION, "revision": os.environ.get("K_REVISION", "local"),
            "cold_start": cold, "uptime_s": round(time.time() - STARTED, 2)}

@app.get("/")
def hello():
    with _lock: _state["requests"] += 1; cold = _state["requests"] == 1
    return jsonify(message=f"scale-api {VERSION}", **_meta(cold))

@app.get("/score")
def score():
    n = min(int(request.args.get("n", 200000)), 5_000_000)
    t0 = time.perf_counter()
    acc = 0.0
    for i in range(1, n):                 # CPU-bound on purpose: concurrency shares this CPU
        acc += math.sqrt(i) / (i + 1)
    with _lock: _state["requests"] += 1; cold = _state["requests"] == 1
    return jsonify(score=round(acc, 3), n=n, ms=round((time.perf_counter() - t0) * 1000, 1), **_meta(cold))

@app.get("/count")
def count():
    with _lock:
        _state["count"] += 1; _state["requests"] += 1
        return jsonify(count=_state["count"], **_meta(False))

@app.get("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
