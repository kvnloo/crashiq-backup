"""Data for the CrashIQ test tracker (the one-page progress report the user reads instead of the workbook).

Writes small CSVs to data/statewide/tracker/, every number computed here from the run history, the latest run's
results and the repo's bug issues, so the page only displays them:

  runs.csv         one row per run on the frozen corridor list (v1), from run_history.csv
  runs_v2.csv      the corridor-list-v2 series, from run_history_corridors_v2.csv
  causes.csv       latest run: why corridors warn or fail (one cause per corridor, as on the workbook's Problems sheet)
  bugs.csv         every GitHub issue labelled bug, open or closed
  recon.csv        latest reconciliation (crash by crash, previous run -> latest)
  context.csv      one row of standing facts (agencies, TIMS, hidden-GPS accuracy, San Jose)

Run: python tests/statewide/build_tracker.py   (after build_workbook.py --record)
"""

from __future__ import annotations

import csv
import json
import statistics
import subprocess
from collections import Counter
from pathlib import Path

import build_workbook as bw
import run_history
import tims_compare

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
OUT = DATA / "tracker"

RUN_COLS = ["run", "date", "app_commit", "fixes_since_last", "cities_tested_v1", "pass_v1", "warn_v1", "fail_v1",
            "pass_v4", "warn_v4", "fail_v4", "silent_drops_v1", "silent_drops_v2", "silent_drops_v3",
            "silent_drops_v4", "located_pct_v1", "on_corridor_located_pct_v2", "unplaced_no_cross_street_v2",
            "unplaced_relaxed_held_v2", "corridor_crashes_v1"]


def _write(name: str, cols: list[str], rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def runs(path: Path) -> list[dict]:
    _, rows = run_history._read(path)
    return [{c: r.get(c, "") for c in RUN_COLS} for r in rows]


def causes(results: list[dict]) -> list[dict]:
    ag = {a["ncic"]: a for a in json.loads((DATA / "agencies.json").read_text())}
    n = Counter(bw.cause({**r, "result": r.get("result_v4") or r["result"]}, ag) for r in results
                if (r.get("result_v4") or r["result"]) in ("warn", "fail"))
    return [{"cause": c, "corridors": k} for c, k in n.most_common()]


def bugs() -> list[dict]:
    out = subprocess.run(["gh", "issue", "list", "--label", "bug", "--state", "all", "--limit", "200", "--json",
                          "number,title,state,createdAt,closedAt"], capture_output=True, text=True, cwd=ROOT,
                         check=True).stdout
    rows = json.loads(out)
    return [{"issue": f"#{r['number']}", "number": r["number"], "title": r["title"].removeprefix("Bug: "),
             "state": r["state"].lower(), "opened": r["createdAt"][:10], "closed": (r["closedAt"] or "")[:10]}
            for r in sorted(rows, key=lambda r: (r["state"] != "OPEN", -r["number"]))]


def recon(before: str, after: str) -> list[dict]:
    f = DATA / f"reconcile_{before}_{after}.json"
    if not f.exists():
        return []
    rc = json.loads(f.read_text())
    sc = rc["same_crashes"]
    rows = [{"bucket": b["what"], "cause": b["cause"], "crashes": b["crashes"], "change_in_kept": b["change_in_kept"],
             "change_in_located": b["change_in_located"]} for b in rc["buckets"] if b["crashes"] and
            b["bucket"] != "unchanged"]
    return [{"same_crashes": sc["kept_in_both"], "located_before_pct": round(100 * sc["located_run1"] /
                                                                             sc["kept_in_both"], 1),
             "located_after_pct": round(100 * sc["located_run2"] / sc["kept_in_both"], 1),
             "kept_before": rc["kept"][0], "kept_after": rc["kept"][1], "located_before": rc["located"][0],
             "located_after": rc["located"][1], **r} for r in rows]


def context(results: list[dict]) -> dict:
    ag = json.loads((DATA / "agencies.json").read_text())
    local = [a for a in ag if a["type"] == "local"]
    acc = json.loads((DATA / "accuracy_by_agency.json").read_text())
    ex = [a["exact_intersection_acc_pct"] for a in acc if a.get("exact_intersection_acc_pct") is not None]
    tims = tims_compare.compare(DATA / "ccrs_mirror.sqlite", bw.TIMS_DIR)
    counties = {r["county"] for r in tims if r["year"] <= 2024 and r.get("tims_fi") is not None}
    sj = next((r for r in results if r["city"] == "San Jose"), {})
    return {"low_gps_agencies": sum(1 for a in local if a["street_gps_pct"] < 20 and a["crashes"] >= 100),
            "collapse_agencies": sum(1 for a in local if a.get("drop_ratio") is not None and a["drop_ratio"] < 0.5
                                     and (a.get("base_2016_19") or 0) >= 50),
            "tims_counties_within_2pct": run_history.tims_within(tims), "tims_counties_compared": len(counties),
            "exact_accuracy_median_pct": round(statistics.median(ex), 1) if ex else None,
            "agencies_accuracy_tested": len(ex),
            "san_jose_result": sj.get("result_v4") or sj.get("result")}


def main() -> None:
    vs = bw.versions()
    ver, before = vs[-1], (vs[-2] if len(vs) > 1 else None)
    results = bw.load_results(ver)
    _write("runs.csv", RUN_COLS, runs(run_history.HISTORY))
    _write("runs_v2.csv", RUN_COLS, runs(run_history.HISTORY_V2))
    _write("causes.csv", ["cause", "corridors"], causes(results))
    _write("bugs.csv", ["issue", "number", "title", "state", "opened", "closed"], bugs())
    rr = recon(before, ver) if before else []
    _write("recon.csv", list(rr[0]) if rr else ["bucket"], rr)
    cx = context(results)
    _write("context.csv", list(cx), [cx])
    print(f"tracker data for {ver} -> {OUT}")


if __name__ == "__main__":
    main()
