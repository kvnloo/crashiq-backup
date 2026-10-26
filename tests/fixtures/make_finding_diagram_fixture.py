"""Writes frontend/src/__fixtures__/finding_diagram.json: GET /findings/{id}/diagram for the Crenshaw fixtures' first
intersection finding, with that finding and its records (#268). Separate from make_frontend_fixtures.py, whose other
fixtures predate the diagram (python3 tests/fixtures/make_finding_diagram_fixture.py, from the repo root)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "tests")]
from fastapi.testclient import TestClient  # noqa: E402

from crashiq.db import Database  # noqa: E402
from crashiq.server import create_app  # noqa: E402
from crashiq.settings import Settings  # noqa: E402
from test_signals import _study  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
s = Settings(db_path=":memory:", app_password=None, anthropic_api_key=None, typesafe_api_key=None,
             study_ai_cap_usd=1.0, dist_dir=ROOT / "nope", fixtures_dir=FIX)
with TestClient(create_app(s, Database(":memory:"))) as c:
    sid = _study(c)
    c.post(f"/api/studies/{sid}/findings/screen")
    fs = c.get(f"/api/studies/{sid}/findings").json()["findings"]
    f = next(x for x in fs if x["meta"]["kind"] == "intersection")
    out = {"finding": f, "records": c.get(f"/api/studies/{sid}/findings/{f['id']}/records").json()["records"],
           "diagram": c.get(f"/api/studies/{sid}/findings/{f['id']}/diagram").json()}
(ROOT / "frontend" / "src" / "__fixtures__" / "finding_diagram.json").write_text(json.dumps(out))
print("wrote finding_diagram.json", f["id"], len(out["records"]), "records")
