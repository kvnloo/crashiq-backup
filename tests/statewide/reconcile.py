"""Run-to-run reconciliation (#73, PM review of #124): every crash in either run lands in exactly one cause bucket.

Per city, on the same frozen corridor, crashes are matched by Collision Id between the app's stored pulls of two
runs. Each crash has a status per run:
  absent      not in that run's pull
  located     kept for the corridor (no exclusion rule) with a location (GPS or auto-placed)
  unlocated   kept for the corridor without a location (review list)
  excluded    pulled but excluded under a rule (side street, private property, grade separation, ...)
The bucket is decided by the first matching rule below (order matters, every crash gets exactly one). The table
reports, per bucket, the crash count and its contribution to the change in corridor crashes (kept, not excluded)
and in located crashes; the contributions add up exactly to the run-to-run change.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import run_history

PLACEHOLDERS = {"", "NOTSTATED", "UNKNOWN", "UNK", "NA", "NONE", "NOSTREET", "PRIVATEPROPERTY"}

BUCKETS = [  # (key, label, cause)
    ("unchanged", "Same status in both runs", "-"),
    ("junk_121", "Placeholder 'NOT STATED' read as the corridor street", "#121 (bug, open)"),
    ("refile_87", "Same crash filed twice: second copy removed", "#81 fix (#87)"),
    ("gps_margin", "GPS crash no longer pulled (beyond the corridor margin)", "#54 (pull drops GPS rows the study "
     "can't use)"),
    ("gps_rule_excluded", "GPS crash now excluded by a pull rule", "#74 / #82 / #67 rules"),
    ("no_cross_review", "No cross street: kept for review instead of excluded or missed", "#82 / #94 (user decision)"),
    ("private_property", "Private property: its own exclusion rule", "#82"),
    ("found_located", "Newly found and located", "#80 #83 #111 #113 (search fixes)"),
    ("found_unlocated", "Newly found, no location (review)", "#80 #83 #111 #113 (search fixes)"),
    ("found_excluded", "Newly found, excluded (side street / other rule)", "#80 #83 #111 #113 (search fixes)"),
    ("other_city_142", "Report filed in a city the corridor doesn't enter: no longer pulled", "#142 (#145)"),
    ("area_rejected_132", "Search area with no GPS crashes near the corridor: no longer searched", "#132 (#141)"),
    ("restored_147", "Report filed under an unincorporated place's own name: pulled again", "#147 (#152)"),
    ("junk_removed_121", "Placeholder 'NOT STATED' no longer read as the corridor street", "#121 (#131)"),
    ("lost", "In the earlier run, not pulled in the later one (other reason)", "other"),
    ("placement_changed", "Kept in both runs, location status changed", "placement / gate"),
    ("rule_changed", "Exclusion status changed (other)", "other"),
]
LABEL = {k: (lbl, cause) for k, lbl, cause in BUCKETS}


def _sq(t) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(t or "").upper())


def status(c: dict | None) -> str:
    if c is None:
        return "absent"
    if c.get("exclude_rule"):
        return "excluded"
    return "unlocated" if c.get("location_source") == "unmatched" else "located"


def _city_allowed(city, cc: dict | None) -> bool | None:
    """Same rule as the app's #142 filter, from the later run's logged corridor cities (None = filter off)."""
    if cc is None:
        return None
    from crashiq.crashes import city_key
    allowed = {city_key(x) for x in cc.get("cities", [])}
    if cc.get("outside"):
        allowed |= {"UNINCORPORATED"} | {city_key(x) for x in cc.get("counties", [])}
    return city_key(city) in allowed


def bucket(c1: dict | None, c2: dict | None, core: str, refiled: set[str], ctx: dict | None = None) -> str:
    s1, s2 = status(c1), status(c2)
    r1, r2 = (c1 or {}).get("exclude_rule"), (c2 or {}).get("exclude_rule")
    if s1 == s2 and r1 == r2:
        return "unchanged"
    c = c2 or c1
    sec, pri = _sq(c.get("secondary_road")), _sq(c.get("primary_road"))
    if c2 is not None and core and len(core) >= 3 and (sec in PLACEHOLDERS and core in sec and core not in pri):
        return "junk_121"
    if c2 is None and str(c1["crash_id"]) in refiled:
        return "refile_87"
    if c2 is None and s1 in ("located", "excluded") and c1.get("location_source") == "gps":
        return "gps_margin"
    if c2 is None and ctx:
        if (core and len(core) >= 3 and _sq(c1.get("secondary_road")) in PLACEHOLDERS and core in
                _sq(c1.get("secondary_road")) and core not in _sq(c1.get("primary_road"))):
            return "junk_removed_121"
        if ctx.get("cities_logged") and _city_allowed(c1.get("city"), ctx.get("corridor_cities")) is False:
            return "other_city_142"
        if str(c1.get("county_code")) in ctx.get("rejected_areas", set()):
            return "area_rejected_132"
    if (c1 is None and ctx and ctx.get("before_cities_logged")
            and _city_allowed(c2.get("city"), ctx.get("before_corridor_cities")) is False):
        return "restored_147"
    if s1 == "located" and s2 == "excluded" and c1.get("location_source") == "gps":
        return "gps_rule_excluded"
    if s2 == "unlocated" and c2.get("review_reason") == "no_cross_street":
        return "no_cross_review"
    if r2 == "private_property":
        return "private_property"
    if c1 is None:
        return {"located": "found_located", "unlocated": "found_unlocated"}.get(s2, "found_excluded")
    if c2 is None:
        return "lost"
    if s1 in ("located", "unlocated") and s2 in ("located", "unlocated"):
        return "placement_changed"
    return "rule_changed"


def reconcile(before: list[dict], after: list[dict], dbs: list[Path]) -> dict:
    """Like-for-like cities only (same frozen corridor line in both runs)."""
    b_by = {(r["city"], r["county"]): r for r in before}
    pairs = [(b_by[(r["city"], r["county"])], r) for r in after if (r["city"], r["county"]) in b_by
             and (b_by[(r["city"], r["county"])].get("corridor") or {}).get("line")
             == (r.get("corridor") or {}).get("line") and r.get("study_id") and b_by[(r["city"], r["county"])].get("study_id")]
    pays = run_history._payloads([x for p in pairs for x in p], dbs)
    import run_cities
    from crashiq import assign as assign_mod
    from crashiq import network as network_mod
    from crashiq import study as study_mod
    from crashiq.db import Database
    app_dbs = [Database(d) for d in dbs if d.exists()]
    gps_check = Counter()                          # where run 1's assignment put the GPS crashes run 2 no longer pulls
    city_dropped_located = Counter()               # located crashes the #142 city filter removed, by placement tier
    city_examples = []
    rows = Counter()
    d_kept, d_loc = Counter(), Counter()
    per_city = []
    both_kept = Counter()                          # like-for-like located %: crashes kept in both runs
    for r1, r2 in pairs:
        p1, p2 = pays.get(r1["study_id"]), pays.get(r2["study_id"])
        if not p1 or not p2:
            continue
        m1 = {str(c["crash_id"]): c for c in p1["crashes"]}
        m2 = {str(c["crash_id"]): c for c in p2["crashes"]}
        refiled = {str(i) for g in p2["cleaning"].get("same_crash_refiled", []) for i in g.get("dropped", [])}
        core = run_cities.indep_core(r2.get("corridor_name") or (r2.get("corridor") or {}).get("road"))
        lg = p2["cleaning"]
        ctx = {"cities_logged": "corridor_cities" in lg, "corridor_cities": lg.get("corridor_cities"),
               "rejected_areas": {str(a.get("area")) for a in lg.get("area_rejected") or []},
               "before_cities_logged": "corridor_cities" in p1["cleaning"],
               "before_corridor_cities": p1["cleaning"].get("corridor_cities")}
        cb = Counter()
        gone = []
        for cid in set(m1) | set(m2):
            c1, c2 = m1.get(cid), m2.get(cid)
            k = bucket(c1, c2, core, refiled, ctx)
            s1, s2 = status(c1), status(c2)
            rows[k] += 1
            cb[k] += 1
            if k == "gps_margin" and s1 == "located":
                gone.append(c1)
            if k == "other_city_142" and s1 == "located":
                city_dropped_located[c1.get("location_source")] += 1
                if len(city_examples) < 8 and not any(x.startswith(f"{r2['city']} corridor") for x in city_examples):
                    city_examples.append(f"{r2['city']} corridor ({r2.get('corridor_name')}): report filed in "
                                         f"{c1.get('city')}, {c1.get('primary_road')} & {c1.get('secondary_road')}, "
                                         f"placed '{c1.get('location_source')}' in the earlier run")
            d_kept[k] += (s2 in ("located", "unlocated")) - (s1 in ("located", "unlocated"))
            d_loc[k] += (s2 == "located") - (s1 == "located")
            if s1 in ("located", "unlocated") and s2 in ("located", "unlocated"):
                both_kept["n"] += 1
                both_kept["loc1"] += s1 == "located"
                both_kept["loc2"] += s2 == "located"
        if gone:
            db = next(d for d in app_dbs if d.one("SELECT 1 FROM study WHERE id = ?", (r1["study_id"],)))
            st = study_mod.require(db, r1["study_id"])
            a = assign_mod.assign(gone, network_mod.network(db, r1["study_id"]), st["radius_ft"], st["buffer_ft"],
                                  bool(st.get("include_freeway")))
            gps_check.update(f"{x['kind']}: {x.get('rule')}" for x in a["assignments"])
        per_city.append({"city": r2["city"], "county": r2["county"], **{k: cb.get(k, 0) for k, _, _ in BUCKETS}})
    kept1 = kept2 = loc1 = loc2 = 0
    for r1, r2 in pairs:
        p1, p2 = pays.get(r1["study_id"]), pays.get(r2["study_id"])
        if p1 and p2:
            kept1 += sum(status(c) in ("located", "unlocated") for c in p1["crashes"])
            kept2 += sum(status(c) in ("located", "unlocated") for c in p2["crashes"])
            loc1 += sum(status(c) == "located" for c in p1["crashes"])
            loc2 += sum(status(c) == "located" for c in p2["crashes"])
    assert sum(d_kept.values()) == kept2 - kept1 and sum(d_loc.values()) == loc2 - loc1, "waterfall doesn't add up"
    return {"cities": len(per_city), "kept": (kept1, kept2), "located": (loc1, loc2),
            "gps_no_longer_pulled_run1_assignment": dict(gps_check.most_common()),
            "located_removed_by_city_filter": {"by_tier": dict(city_dropped_located), "examples": city_examples},
            "buckets": [{"bucket": k, "what": LABEL[k][0], "cause": LABEL[k][1], "crashes": rows.get(k, 0),
                         "change_in_kept": d_kept.get(k, 0), "change_in_located": d_loc.get(k, 0)}
                        for k, _, _ in BUCKETS],
            "same_crashes": {"kept_in_both": both_kept["n"], "located_run1": both_kept["loc1"],
                             "located_run2": both_kept["loc2"]},
            "per_city": per_city}


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[2]
    data = root / "data" / "statewide"
    b, a = sys.argv[1], sys.argv[2]
    load = lambda v: [json.loads(f.read_text()) for f in sorted((data / "results" / v).glob("*.json"))]  # noqa: E731
    res = reconcile(load(b), load(a), [root / "data" / "tester.sqlite", *sorted(data.glob("tester_worker*.sqlite"))])
    (data / f"reconcile_{b}_{a}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "per_city"}, indent=1))
