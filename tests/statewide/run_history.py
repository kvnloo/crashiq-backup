"""Run history (#73, user requirement 2026-10-19): one appended row per statewide run, never overwritten.

Files (in the repo, so history survives the machine):
  tests/statewide/run_history.csv         one row per run (per backend code version)
  tests/statewide/run_history_cities.csv  one row per city per run (result, coverage, silent drops)

Rules:
- A run is recorded once, keyed on its backend tree. Recording again for the same tree changes nothing.
- Existing rows are never edited or deleted. New rows are appended.
- Every measure column carries its definition version (`_v1`). A measure whose definition changes gets a new column
  (`_v2`); old rows keep their old value and leave the new column blank. Definitions: `MEASURES`.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sqlite3
import subprocess
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HISTORY = HERE / "run_history.csv"
CITY_HISTORY = HERE / "run_history_cities.csv"
UNUSABLE = {"", "NOTSTATED", "PRIVATEPROPERTY", "UNKNOWN", "NONE", "NA", "PARKINGLOT"}

MEASURES = {
    "corridor_crashes_v1": "Crashes the pull kept as corridor candidates (not excluded at pull time), all tested cities.",
    "located_pct_v1": "Of corridor candidates: % with GPS or auto-placed by the locator (coverage, not accuracy).",
    "review_pct_v1": "Of corridor candidates: % left unplaced with a locator suggestion (the review list).",
    "unplaced_pct_v1": "Of corridor candidates: % left unplaced with no suggestion.",
    "cities_tested_v1": "Cities run through the app on a frozen corridor (result pass, warn or fail).",
    "pass_v1": "Cities with result pass (rules on the Method sheet).", "warn_v1": "Cities with result warn.",
    "fail_v1": "Cities with result fail.", "pass_pct_v1": "pass / cities tested, %.",
    "silent_drops_v1": "No-GPS reports naming the corridor and a study cross street, in the city, that the app never "
                       "pulled (independent SQL on the mirror).",
    "double_counts_v1": "Extra crashes among those pulled: same agency + report number + both roads under 2+ "
                        "Collision Ids (each group counts n-1).",
    "excluded_wrongly_v1": "Crashes excluded as a side street (#39 rule) whose cross street is blank / NOT STATED / "
                           "PRIVATE PROPERTY: the report names no side street (#82).",
    "tims_counties_within_2pct_v1": "Counties whose CCRS fatal+injury crashes 2021-2024 (final years, by crash date) "
                                    "are within +/-2% of TIMS's.",
    "placement_accuracy_pct_v1": "Hidden-GPS test (#88): % of auto-placed crashes within the gate distance of their "
                                 "own GPS. Blank until #88 exists.",
}
RUN_COLS = ["run", "date", "app_commit", "backend_tree", "mirror_date", "years", "corridor_list", "fixes_since_last"]


def _git(*a) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True).stdout.strip()


def _read(path: Path) -> tuple[list[str], list[dict]]:
    if not path.exists():
        return [], []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def _append(path: Path, rows: list[dict], cols: list[str]) -> None:
    """Append rows; if new columns appear, rewrite the header only (existing values untouched, new cells blank)."""
    old_cols, old = _read(path)
    allc = old_cols + [c for c in cols if c not in old_cols]
    if allc != old_cols and old:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, allc)
            w.writeheader()
            w.writerows(old)
    new_file = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, allc)
        if new_file:
            w.writeheader()
        w.writerows(rows)


def _payloads(results: list[dict], dbs: list[Path]) -> dict[str, dict]:
    """study_id -> the app's cached pull (crashes + cleaning log) from the Tester databases."""
    want = {r["study_id"] for r in results if r.get("study_id")}
    out = {}
    for db in dbs:
        if not db.exists():
            continue
        con = sqlite3.connect(db)
        for sid, payload in con.execute("SELECT study_id, payload FROM crash_pull"):
            if sid in want:
                out[sid] = json.loads(payload)
        con.close()
    return out


def _report_numbers(mirror_db: Path, ids: set[str]) -> dict[str, tuple]:
    con = sqlite3.connect(mirror_db)
    out = {}
    idl = sorted(int(i) for i in ids if str(i).isdigit())
    for (rid,) in con.execute("SELECT rid FROM _meta WHERE tbl = 'crashes'"):
        for i in range(0, len(idl), 900):
            chunk = idl[i:i + 900]
            q = (f'SELECT "Collision Id", "NCIC Code", "Report Number", "PrimaryRoad", "SecondaryRoad" FROM "{rid}" '
                 f'WHERE "Collision Id" IN ({",".join("?" * len(chunk))})')
            for cid, a, rep, p, s in con.execute(q, chunk):
                sq = lambda t: re.sub(r"[^A-Z0-9]", "", str(t or "").upper())  # noqa: E731
                out[str(int(cid))] = (str(a), str(rep or "").strip(), *sorted((sq(p), sq(s))))
    con.close()
    return out


def city_measures(results: list[dict], dbs: list[Path], mirror_db: Path) -> dict[str, dict]:
    """Per city (key 'city|county'): coverage split, double counts, wrongly excluded, from the app's own pull."""
    pays = _payloads(results, dbs)
    ids = {str(c["crash_id"]) for p in pays.values() for c in p["crashes"]}
    reps = _report_numbers(mirror_db, ids)
    out = {}
    for r in results:
        p = pays.get(r.get("study_id") or "")
        m = {"located": None, "review": None, "unplaced": None, "candidates": None, "double_counts": None,
             "excluded_wrongly": None}
        if p:
            cand = [c for c in p["crashes"] if not c.get("exclude_rule")]
            un = [c for c in cand if c.get("location_source") == "unmatched"]
            groups = defaultdict(set)
            for c in p["crashes"]:
                k = reps.get(str(c["crash_id"]))
                if k and k[1]:
                    groups[k].add(str(c["crash_id"]))
            sq = lambda t: re.sub(r"[^A-Z0-9]", "", str(t or "").upper())  # noqa: E731
            m = {"candidates": len(cand), "located": len(cand) - len(un),
                 "review": sum(1 for c in un if c.get("suggestion")),
                 "unplaced": sum(1 for c in un if not c.get("suggestion")),
                 "double_counts": sum(len(v) - 1 for v in groups.values() if len(v) > 1),
                 "excluded_wrongly": sum(1 for c in p["crashes"] if c.get("exclude_rule") == "cross_street_not_on_corridor"
                                         and (sq(c.get("secondary_road")) in UNUSABLE or len(sq(c.get("secondary_road"))) <= 2))}
        out[f"{r['city']}|{r['county']}"] = m
    return out


def tims_within(tims_rows: list[dict], tol_pct: float = 2.0) -> int | None:
    tot = defaultdict(lambda: [0, 0])
    for r in tims_rows:
        if r["year"] <= 2024 and r.get("tims_fi") is not None:
            tot[r["county"]][0] += r["ccrs_fi"]
            tot[r["county"]][1] += r["tims_fi"]
    if not tot:
        return None
    return sum(1 for c, t in tot.values() if t and abs(c - t) / t * 100 <= tol_pct)


def _fixes(prev_commit: str | None, commit: str) -> str:
    if not prev_commit:
        return "baseline (first run)"
    subjects = _git("log", "--format=%s", f"{prev_commit}..{commit}").splitlines()
    nums = sorted({n for s in subjects if re.match(r"(fix|feat)", s) for n in re.findall(r"#(\d+)", s)}, key=int)
    return ", ".join(f"#{n}" for n in nums) or "none"


def record(results: list[dict], tims_rows: list[dict], dbs: list[Path], mirror_db: Path, corridor_list: str) -> dict:
    """Append this run (once) to both history files; returns its row."""
    tree = next((r.get("code_version") for r in results if r.get("code_version")), "")
    _, runs = _read(HISTORY)
    for row in runs:
        if row.get("backend_tree") == tree:
            return row                                         # already recorded: never rewritten
    cm = city_measures(results, dbs, mirror_db)
    tested = [r for r in results if r.get("result") in ("pass", "warn", "fail")]
    cand = sum(cm[f"{r['city']}|{r['county']}"]["candidates"] or 0 for r in tested)

    def pct(key):
        return round(100 * sum(cm[f"{r['city']}|{r['county']}"][key] or 0 for r in tested) / cand, 2) if cand else None
    n = {k: sum(1 for r in tested if r["result"] == k) for k in ("pass", "warn", "fail")}
    first = next((r for r in results if r.get("commit")), {})
    row = {"run": len(runs) + 1, "date": dt.date.today().isoformat(),
           "app_commit": first.get("commit"), "backend_tree": tree, "mirror_date": first.get("mirror_built"),
           "years": "2021-2025", "corridor_list": corridor_list,
           "fixes_since_last": _fixes(runs[-1]["app_commit"] if runs else None, first.get("commit") or "HEAD"),
           "corridor_crashes_v1": cand, "located_pct_v1": pct("located"), "review_pct_v1": pct("review"),
           "unplaced_pct_v1": pct("unplaced"), "cities_tested_v1": len(tested),
           "pass_v1": n["pass"], "warn_v1": n["warn"], "fail_v1": n["fail"],
           "pass_pct_v1": round(100 * n["pass"] / len(tested), 1) if tested else None,
           "silent_drops_v1": sum(r.get("silent_drops") or 0 for r in tested),
           "double_counts_v1": sum(cm[f"{r['city']}|{r['county']}"]["double_counts"] or 0 for r in tested),
           "excluded_wrongly_v1": sum(cm[f"{r['city']}|{r['county']}"]["excluded_wrongly"] or 0 for r in tested),
           "tims_counties_within_2pct_v1": tims_within(tims_rows), "placement_accuracy_pct_v1": None}
    _append(HISTORY, [row], RUN_COLS + list(MEASURES))
    crow = []
    for r in results:
        m = cm[f"{r['city']}|{r['county']}"]
        crow.append({"run": row["run"], "city": r["city"], "county": r["county"], "result": r.get("result"),
                     "reason": r.get("result_reason"), "candidates_v1": m["candidates"], "located_v1": m["located"],
                     "silent_drops_v1": r.get("silent_drops"), "double_counts_v1": m["double_counts"],
                     "excluded_wrongly_v1": m["excluded_wrongly"]})
    _append(CITY_HISTORY, crow, list(crow[0]) if crow else [])
    return row
