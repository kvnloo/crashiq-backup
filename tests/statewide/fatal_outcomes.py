"""Fatal crashes on the test corridors, by outcome, for one statewide run (#178: before/after FARS, #174).

Uses that run's own backend code and stored pulls (same basis): for each fatal crash the pull kept, where the app's
assignment put it: placed at a study location (by provenance: gps, exact, fars, ...), excluded (by rule, incl.
fars_off_corridor), or left unplaced (with or without a FARS hint). The same reading run_cities.py records from run 6.

Run: python tests/statewide/fatal_outcomes.py <backend_tree> <checkout of that run's commit>
Writes data/statewide/fatal_outcomes_<tree>.json.
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


def outcome(c: dict, a: dict) -> str:
    if a.get("kind") in ("intersection", "segment"):
        return f"placed_{c.get('location_source')}"
    if a.get("kind") == "excluded":
        return f"excluded_{a.get('rule')}"
    if c.get("location_source") == "unmatched":
        return "unplaced_with_fars_hint" if c.get("fars_hint") else "unplaced"
    return f"other_{a.get('kind')}"


def main(tree: str, code: Path) -> None:
    sys.path.insert(0, str(code / "backend"))
    from crashiq import assign
    from crashiq.db import Database
    results = [json.loads(p.read_text()) for p in sorted((DATA / "results" / tree).glob("*.json"))]
    want = {r["study_id"] for r in results if r.get("study_id")}
    tot, by_city, crashes = Counter(), {}, []
    for dbp in [ROOT / "data" / "tester.sqlite", *sorted(DATA.glob("tester_worker*.sqlite"))]:
        con = sqlite3.connect(dbp)
        sids = [s for (s,) in con.execute("SELECT id FROM study") if s in want]
        con.close()
        db = Database(dbp)
        for sid in sids:
            _, _, pull, a = assign.for_study(db, sid)
            akind = {str(x["crash_id"]): x for x in a["assignments"]}
            fatal = [c for c in pull["crashes"] if (c.get("killed") or 0) > 0 and not c.get("exclude_rule")]
            n = Counter(outcome(c, akind.get(str(c["crash_id"]), {})) for c in fatal)
            for c in fatal:
                x = akind.get(str(c["crash_id"]), {})
                crashes.append({"study": sid, "crash_id": str(c["crash_id"]), "outcome": outcome(c, x),
                                "location_id": x.get("location_id"), "distance_ft": x.get("distance_ft"),
                                "roads": [c.get("primary_road"), c.get("secondary_road")], "city": c.get("city"),
                                "lat": c.get("lat"), "lon": c.get("lon"), "fars_case": c.get("fars_case")})
            tot.update(n)
            by_city[sid] = dict(n)
        db.close()
    city_of = {r["study_id"]: r["city"] for r in results if r.get("study_id")}
    for c in crashes:
        c["test_city"] = city_of.get(c.pop("study"))
    out = {"tree": tree, "studies": len(by_city), "fatal_outcomes": dict(tot.most_common()), "crashes": crashes}
    (DATA / f"fatal_outcomes_{tree}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "crashes"}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
