"""Statewide Findings run (#176, measure only): the code findings (C7, written from T12) for every corridor of one
statewide run, on that run's own backend code and stored pulls (same basis).

For each city: locations screened (T2 rows), T12 rows flagged, how many used the binomial fallback, findings shown,
and findings the validator rejected (expected 0: a code finding's numbers all come from T12).

Run: python tests/statewide/findings_run.py <backend_tree> <path to a checkout of that run's commit>
Writes data/statewide/findings_<tree>.json.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"


def main(tree: str, code: Path) -> None:
    sys.path.insert(0, str(code / "backend"))
    from crashiq.db import Database
    from crashiq.server import create_app
    from crashiq.settings import Settings
    from fastapi.testclient import TestClient
    results = [json.loads(p.read_text()) for p in sorted((DATA / "results" / tree).glob("*.json"))]
    results = [r for r in results if r.get("study_id")]
    dbs = [ROOT / "data" / "tester.sqlite", *sorted(DATA.glob("tester_worker*.sqlite"))]
    where = {}
    for db in dbs:
        con = sqlite3.connect(db)
        where.update({sid: db for (sid,) in con.execute("SELECT id FROM study")})
        con.close()
    out = []
    for db in dbs:
        mine = [r for r in results if where.get(r["study_id"]) == db]
        if not mine:
            continue
        settings = Settings(db_path=db, app_password=None, anthropic_api_key=None, typesafe_api_key=None,
                            study_ai_cap_usd=0.0, dist_dir=ROOT / "no-dist", fixtures_dir=None)
        app = create_app(settings, Database(settings.db_path))
        with TestClient(app) as client:
            for r in mine:
                sid = r["study_id"]
                row = {"city": r["city"], "county": r["county"], "result": r.get("result_v4") or r.get("result")}
                pr = client.get(f"/api/studies/{sid}/profile")
                if pr.status_code != 200:
                    out.append({**row, "error": f"profile HTTP {pr.status_code}"})
                    continue
                tabs = {t["id"]: t for t in pr.json()["tables"]}
                t12 = tabs.get("T12", {}).get("rows", [])
                sc = client.post(f"/api/studies/{sid}/findings/screen")
                if sc.status_code != 200:
                    out.append({**row, "error": f"screen HTTP {sc.status_code}: {sc.text[:200]}"})
                    continue
                s = sc.json()
                out.append({**row, "locations_screened": len(tabs.get("T2", {}).get("rows", [])),
                            "t12_rows": len(t12),
                            "t12_binomial": sum(1 for x in t12 if x["values"]["method"].startswith("Binomial")),
                            "t12_strong": sum(1 for x in t12 if x["values"]["strength"] == "Strong"),
                            "findings_shown": len(s["shown"]), "findings_rejected": len(s["rejected"]),
                            "rejected_reasons": [x["reasons"] for x in s["rejected"]],
                            "binomial_findings": sum(1 for f in s["shown"]
                                                     if "binomial" in json.dumps(f).lower())})
                print(f"{r['city']}: {out[-1].get('findings_shown')} findings, {out[-1].get('findings_rejected')} "
                      f"rejected", flush=True)
    summ = {"tree": tree, "cities": len(out), "errors": sum(1 for x in out if "error" in x),
            "with_findings": sum(1 for x in out if x.get("findings_shown")),
            "findings": sum(x.get("findings_shown") or 0 for x in out),
            "rejected": sum(x.get("findings_rejected") or 0 for x in out),
            "t12_rows": sum(x.get("t12_rows") or 0 for x in out),
            "t12_binomial": sum(x.get("t12_binomial") or 0 for x in out),
            "locations_screened": sum(x.get("locations_screened") or 0 for x in out),
            "by_result": dict(Counter(x["result"] for x in out if x.get("findings_shown")))}
    (DATA / f"findings_{tree}.json").write_text(json.dumps({"summary": summ, "cities": out}, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
