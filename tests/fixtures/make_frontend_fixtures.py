"""Writes frontend/src/__fixtures__/*.json from the backend run on the Crenshaw fixtures, so frontend tests
assert against real API responses (python3 tests/fixtures/make_frontend_fixtures.py, from the repo root)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "tests")]
from fastapi.testclient import TestClient  # noqa: E402

from crashiq.db import Database  # noqa: E402
from crashiq.server import create_app  # noqa: E402
from crashiq.settings import Settings  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
OUT = ROOT / "frontend" / "src" / "__fixtures__"
s = Settings(db_path=":memory:", app_password=None, anthropic_api_key=None, typesafe_api_key=None,
             study_ai_cap_usd=1.0, dist_dir=ROOT / "nope", fixtures_dir=FIX)
with TestClient(create_app(s, Database(":memory:"))) as c:
    sid = c.post("/api/studies", json={"name": "Crenshaw Blvd safety", "mode": "tis"}).json()["id"]
    net = c.put(f"/api/studies/{sid}/corridor", json={"line": [[33.8953, -118.32662], [33.9040, -118.32662], [33.9123, -118.32662]]}).json()
    pull = c.post(f"/api/studies/{sid}/crashes/pull").json()
    prof = c.get(f"/api/studies/{sid}/profile").json()
    crashes = c.get(f"/api/studies/{sid}/crashes").json()
    first = prof["tables"][1]["rows"][0]["key"]
    loc = c.get(f"/api/studies/{sid}/profile/locations/{first}").json()
    for name, obj in {"network": net, "pull": pull, "profile": prof, "crashes": crashes, "location": loc}.items():
        (OUT / f"{name}.json").write_text(json.dumps(obj))
print("wrote", sorted(p.name for p in OUT.glob("*.json")))
