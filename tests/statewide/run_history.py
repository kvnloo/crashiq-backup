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
import sys  # noqa: E402
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[1]
HISTORY = HERE / "run_history.csv"
CITY_HISTORY = HERE / "run_history_cities.csv"
# Corridor list v2 series (PM, PR #148): its own files and its own baseline from run 4, never mixed with v1.
HISTORY_V2 = HERE / "run_history_corridors_v2.csv"
CITY_HISTORY_V2 = HERE / "run_history_corridors_v2_cities.csv"
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
                       "pulled (independent SQL on the mirror; street core from the app's names.py).",
    "silent_drops_v2": "As v1, with the Tester's own street core (leading direction and suffix dropped, #113).",
    "new_corridors_v1": "Cities whose corridor was picked after the corridor list was frozen (not like-for-like with "
                        "earlier runs; the Before-after sheet keeps them separate).",
    "on_corridor_located_pct_v2": "Of crashes that count for the corridor (assigned to a study intersection or "
                                  "segment, or still without a location): % with a location. Replaces located_pct_v1"
                                  "'s denominator, which also held GPS crashes the assignment later excluded.",
    "double_counts_on_corridor_v2": "As double_counts_v1, but only groups with at least one crash that counts for the "
                                    "corridor (v1 also counted crashes excluded anyway). Same-minute refilings are "
                                    "dropped by the app since #81; what's left differs in time.",
    "unplaced_no_cross_street_v2": "Unplaced corridor crashes whose report gives no cross street (blank / NOT STATED): "
                                   "kept for review since #82; they can lie anywhere along the street in the county.",
    "unplaced_relaxed_held_v2": "Unplaced corridor crashes whose locator suggestion is on the 'relaxed' tier (name "
                                "match without the direction), held for review by the exact-only gate (PR #16).",
    "pass_v2": "Cities with result pass under the run-2 rule (Method sheet).", "warn_v2": "Run-2 rule: warn.",
    "fail_v2": "Run-2 rule: fail (adds 0-pulled-while-reports-name-the-street as fail).",
    "double_counts_v1": "Extra crashes among those pulled: same agency + report number + both roads under 2+ "
                        "Collision Ids (each group counts n-1).",
    "excluded_no_cross_street_v1": "Corridor-street crashes the pull excluded under the side-street rule (#39) "
                                   "although the report names no cross street (blank / NOT STATED / PRIVATE "
                                   "PROPERTY, #82). They can lie anywhere along the street in the county, so this is "
                                   "an upper bound on wrong exclusions, not a count of them.",
    "tims_counties_within_2pct_v1": "Counties whose CCRS fatal+injury crashes 2021-2024 (final years, by crash date) "
                                    "are within +/-2% of TIMS's.",
    "silent_drops_v3": "As v2, but a report counts only when its roads ARE the corridor and a study cross street "
                       "(whole street names after normalising, not substrings: 'OLD MIDDLEFIELD WY' is not Middlefield "
                       "Rd), and a refiled copy whose kept twin was pulled doesn't count (PM, PR #148; from run 4).",
    "pass_v3": "Cities with result pass under the run-2 rule using silent_drops_v3.", "warn_v3": "As pass_v3: warn.",
    "fail_v3": "As pass_v3: fail.",
    "silent_drops_v4": "As v3, less reports whose own stated offset from their cross street (CCRS distance, direction, "
                       "unit; computed by the Tester from OSM cross-street nodes and the frozen line, not by the app) "
                       "puts them more than 250 ft (or the study radius) past either end of the stretch. Offsets over "
                       "a mile, or without a direction, never clear a report. Every cleared report is listed on the "
                       "'Silent drops v4 cleared' sheet with its distance (PM, after #149; from run 4).",
    "pass_v4": "Cities with result pass under the run-2 rule using silent_drops_v4.", "warn_v4": "As pass_v4: warn.",
    "fail_v4": "As pass_v4: fail.",
    "gps_dms_corrected_v1": "Corridor crashes whose GPS was written as degrees-minutes-seconds and that the app converted "
                            "after checking it against the report's streets (#143, from run 5).",
    "placement_accuracy_pct_v1": "Hidden-GPS test (#88): % of auto-placed crashes within the gate distance of their "
                                 "own GPS. Blank until #88 exists.",
}
RUN_COLS = ["run", "date", "app_commit", "backend_tree", "mirror_date", "years", "corridor_list", "fixes_since_last",
            "note"]


def correct_run(run: int, results: list[dict], dbs: list[Path], mirror_db: Path, note: str) -> None:
    """A documented correction of a recording error in one run's row (never a redefinition): recompute the
    payload-based measures of that run and say why in its `note`. Other runs and columns are untouched."""
    cols, rows = _read(HISTORY)
    cm = city_measures(results, dbs, mirror_db)
    tested = [r for r in results if r.get("result_v1", r.get("result")) in ("pass", "warn", "fail")]
    get = lambda r, k: cm[f"{r['city']}|{r['county']}"][k] or 0  # noqa: E731
    cand = sum(get(r, "candidates") for r in tested)
    fix = {"corridor_crashes_v1": cand,
           **{f"{k}_pct_v1": round(100 * sum(get(r, k) for r in tested) / cand, 2) if cand else None
              for k in ("located", "review", "unplaced")},
           "double_counts_v1": sum(get(r, "double_counts") for r in tested),
           "excluded_no_cross_street_v1": sum(get(r, "excluded_wrongly") for r in tested)}
    for row in rows:
        if str(row["run"]) == str(run):
            row.update({k: v for k, v in fix.items() if k in cols})
            row["note"] = ((row.get("note") or "") + " " + note).strip()
    _write_atomic(HISTORY, cols + [c for c in ["note"] if c not in cols], rows)


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
        _write_atomic(path, allc, old)
    new_file = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, allc)
        if new_file:
            w.writeheader()
        w.writerows(rows)


def _write_atomic(path: Path, cols: list[str], rows: list[dict]) -> None:
    """Rewrite a history file via a temp file + rename, so a failed write never truncates history."""
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="raise")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


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
             "excluded_wrongly": None, "unplaced_no_cross": None, "unplaced_relaxed": None,
             "double_counts_on_corridor": None}
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
                 "double_counts_on_corridor": sum(len(v) - 1 for v in groups.values() if len(v) > 1
                                                  and any(not c.get("exclude_rule") for c in p["crashes"]
                                                          if str(c["crash_id"]) in v)),
                 "excluded_wrongly": sum(1 for c in p["crashes"] if c.get("exclude_rule") == "cross_street_not_on_corridor"
                                         and (sq(c.get("secondary_road")) in UNUSABLE or len(sq(c.get("secondary_road"))) <= 2)),
                 "unplaced_no_cross": sum(1 for c in un if sq(c.get("secondary_road")) in UNUSABLE
                                          or len(sq(c.get("secondary_road"))) <= 2),
                 "unplaced_relaxed": sum(1 for c in un if (c.get("suggestion") or {}).get("tier") == "relaxed")}
        out[f"{r['city']}|{r['county']}"] = m
    return out


def _on_corridor_pct(results: list[dict]) -> float | None:
    on = sum((r.get("assignment") or {}).get("intersection", 0) + (r.get("assignment") or {}).get("segment", 0)
             for r in results)
    un = sum((r.get("assignment") or {}).get("unmatched", 0) for r in results)
    return round(100 * on / (on + un), 2) if on + un else None


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


class IncompleteRun(RuntimeError):
    """A run with a city missing its result: never recorded (completeness guard)."""


def require_complete(series: str, expected: list[dict], results: list[dict]) -> dict:
    """Raise IncompleteRun naming every city without a result; else return the completeness counts."""
    import checks
    c = checks.completeness(expected, results)
    if not c["complete"]:
        raise IncompleteRun(f"{series}: {len(c['missing'])} of {c['expected']} cities have no result, run NOT "
                            f"recorded: " + ", ".join(c["missing"]))
    return c


def series_v2(v1_results: list[dict], v2_results: list[dict]) -> list[dict]:
    """The corridor-list-v2 series of one code version: v1's results, with each re-picked city's v2 result in place
    of its v1 one (the other v2 corridors are the v1 lines, so their v1 results are theirs)."""
    v2 = {(r["city"], r["county"]): r for r in v2_results}
    return [v2.get((r["city"], r["county"]), r) for r in v1_results]


def record(results: list[dict], tims_rows: list[dict], dbs: list[Path], mirror_db: Path, corridor_list: str,
           history: Path = HISTORY, city_history: Path = CITY_HISTORY) -> dict:
    """Append this run (once) to both history files of its series; returns its row."""
    tree = next((r.get("code_version") for r in results if r.get("code_version")), "")
    _, runs = _read(history)
    for row in runs:
        if row.get("backend_tree") == tree:
            return row                                         # already recorded: never rewritten
    cm = city_measures(results, dbs, mirror_db)
    tested = [r for r in results if r.get("result_v1", r.get("result")) in ("pass", "warn", "fail")]
    cand = sum(cm[f"{r['city']}|{r['county']}"]["candidates"] or 0 for r in tested)

    def pct(key):
        return round(100 * sum(cm[f"{r['city']}|{r['county']}"][key] or 0 for r in tested) / cand, 2) if cand else None
    n = {k: sum(1 for r in tested if r.get("result_v1", r["result"]) == k) for k in ("pass", "warn", "fail")}
    has_v2 = any("result_v1" in r for r in results)
    n2 = {k: sum(1 for r in results if r["result"] == k) for k in ("pass", "warn", "fail")} if has_v2 else {}
    has_v3 = any("result_v3" in r for r in results)
    n3 = {k: sum(1 for r in results if r.get("result_v3") == k) for k in ("pass", "warn", "fail")} if has_v3 else {}
    has_v4 = any(r.get("silent_drops_v4") is not None for r in results)
    n4 = {k: sum(1 for r in results if r.get("result_v4") == k) for k in ("pass", "warn", "fail")} if has_v4 else {}
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
           "excluded_no_cross_street_v1": sum(cm[f"{r['city']}|{r['county']}"]["excluded_wrongly"] or 0 for r in tested),
           "tims_counties_within_2pct_v1": tims_within(tims_rows), "placement_accuracy_pct_v1": None,
           "silent_drops_v2": sum(r.get("silent_drops_v2") or 0 for r in results) if has_v2 else None,
           "pass_v2": n2.get("pass"), "warn_v2": n2.get("warn"), "fail_v2": n2.get("fail"),
           "silent_drops_v3": sum(r.get("silent_drops_v3") or 0 for r in results) if has_v3 else None,
           "pass_v3": n3.get("pass"), "warn_v3": n3.get("warn"), "fail_v3": n3.get("fail"),
           "silent_drops_v4": sum(r.get("silent_drops_v4") or 0 for r in results) if has_v4 else None,
           "pass_v4": n4.get("pass"), "warn_v4": n4.get("warn"), "fail_v4": n4.get("fail"),
           "gps_dms_corrected_v1": (sum(r.get("gps_dms_corrected") or 0 for r in results)
                                    if any("gps_dms_corrected" in r for r in results) else None),
           "new_corridors_v1": sum(1 for r in results if str(r.get("corridor_source", "")).startswith("picked (added")
                                   and (r.get("corridor") or {}).get("line")),
           "on_corridor_located_pct_v2": _on_corridor_pct(tested),
           "double_counts_on_corridor_v2": sum(cm[f"{r['city']}|{r['county']}"].get("double_counts_on_corridor") or 0
                                               for r in tested),
           "unplaced_no_cross_street_v2": sum(cm[f"{r['city']}|{r['county']}"].get("unplaced_no_cross") or 0
                                              for r in tested),
           "unplaced_relaxed_held_v2": sum(cm[f"{r['city']}|{r['county']}"].get("unplaced_relaxed") or 0
                                           for r in tested)}
    _append(history, [row], RUN_COLS + list(MEASURES))
    crow = []
    for r in results:
        m = cm[f"{r['city']}|{r['county']}"]
        crow.append({"run": row["run"], "city": r["city"], "county": r["county"], "result": r.get("result"),
                     "reason": r.get("result_reason"), "result_run1_rule": r.get("result_v1", r.get("result")), "candidates_v1": m["candidates"], "located_v1": m["located"],
                     "silent_drops_v1": r.get("silent_drops"), "double_counts_v1": m["double_counts"],
                     "excluded_no_cross_street_v1": m["excluded_wrongly"],
                     "result_v3": r.get("result_v3"), "silent_drops_v3": r.get("silent_drops_v3"),
                     "result_v4": r.get("result_v4"), "silent_drops_v4": r.get("silent_drops_v4"),
                     "corridor_source": r.get("corridor_source")})
    _append(city_history, crow, list(crow[0]) if crow else [])
    return row
