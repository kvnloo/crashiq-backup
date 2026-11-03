"""Smoke test for the CrashIQ container on an empty disk (#383). Run by hand, needs the network (CCRS, Caltrans, census):

    export APP_PASSWORD=...   # any test value; typed in your shell, never committed
    docker run -d --name crashiq-smoke -p 8001:8000 -e APP_PASSWORD -v crashiq-empty:/var/data crashiq
    python backend/scripts/container_smoke.py

Prints each step's HTTP status and time: auth (health open, everything else 401), corridor, network, first and second
crash pull, profile, findings, review, both exports. If public Overpass is at capacity the corridor step fails with
502; to test the rest, add `-e CRASHIQ_FIXTURES_DIR=/fx -v <folder with overpass_crenshaw.json>:/fx:ro` (Overpass
from the recorded Crenshaw answer, CCRS live).
"""
import base64, json, os, time, urllib.request, urllib.error
B = "http://127.0.0.1:8001"; PW = os.environ["APP_PASSWORD"]
AUTH = {"Authorization": "Basic " + base64.b64encode(f"u:{PW}".encode()).decode()}
def call(method, path, body=None, auth=True, timeout=900):
    req = urllib.request.Request(B + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={**(AUTH if auth else {}), "Content-Type": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(); code = r.status
    except urllib.error.HTTPError as e:
        raw, code = e.read(), e.code
    dt = time.time() - t
    try: data = json.loads(raw)
    except Exception: data = {"bytes": len(raw)}
    return code, data, dt
for _ in range(60):
    try:
        if call("GET", "/api/health", auth=False)[0] == 200: break
    except Exception: time.sleep(1)
print("health no-auth:", call("GET", "/api/health", auth=False)[0])
print("studies no-auth:", call("GET", "/api/studies", auth=False)[0])
print("app page no-auth:", call("GET", "/", auth=False)[0])
c, s, _ = call("POST", "/api/studies", {"name": "Smoke Crenshaw", "mode": "profile"}); sid = s["id"]; print("create:", c)
LINE = [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)]
c, d, dt = call("PUT", f"/api/studies/{sid}/corridor", {"line": LINE}); print(f"corridor: {c} {dt:.1f}s")
c, d, dt = call("GET", f"/api/studies/{sid}/network"); print(f"network (Overpass): {c} {dt:.1f}s", {k: (len(v) if isinstance(v, list) else v) for k, v in d.items() if k in ("intersections", "segments")})
c, d, dt = call("POST", f"/api/studies/{sid}/crashes/pull"); print(f"crash pull (first, empty disk): {c} {dt:.1f}s", {k: d.get(k) for k in ("total", "kept", "in_study", "crashes", "counts") if k in d} or str(d)[:300])
c, d, dt = call("POST", f"/api/studies/{sid}/crashes/pull"); print(f"crash pull (again): {c} {dt:.1f}s")
for p in ("profile", "findings", "review"):
    c, d, dt = call("GET", f"/api/studies/{sid}/{p}"); print(f"{p}: {c} {dt:.1f}s")
for p in ("export.xlsx", "export.pdf"):
    c, d, dt = call("GET", f"/api/studies/{sid}/{p}"); print(f"{p}: {c} {dt:.1f}s {d}")
