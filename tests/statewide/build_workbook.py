"""Write the statewide test workbook (#73) from the cached run outputs. No network; reruns are free.

Inputs:  data/statewide/results/*.json (run_cities.py), data/statewide/agencies.json (agency_scan.py),
         the CCRS mirror + data/cache/statewide/tims/ (tims_compare.py).
Output:  reports/testing/CrashIQ-statewide-test-<date>.xlsx

Every number on Summary is an Excel formula over the data sheets, and the Conclusion sentences are formulas that
quote those cells, so no number is typed by hand (CLAUDE.md: code computes every number).
"""

from __future__ import annotations

import datetime as dt
import csv
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import fields_check  # noqa: E402
import run_history  # noqa: E402
import reconcile  # noqa: E402
import tims_compare  # noqa: E402
from openpyxl.chart import LineChart  # noqa: E402

DATA = ROOT / "data" / "statewide"
TIMS_DIR = ROOT / "data" / "cache" / "statewide" / "tims"
BUGS = {79: "Real CCRS injury codes all became U (no A/B/C, KSI = fatal only). Fixed on main by #76; in this run's code",
        80: "Hyphen in the OSM corridor name stops the no-GPS search (Union City, Saratoga). Fixed on main by #89, after this run",
        81: "One crash filed under two Collision Ids is counted twice. Fixed on main by #87, after this run",
        82: "'NOT STATED' cross street excluded as a side street. Fixed on main, after this run",
        83: "Crashes written by route number (SR-1) not found on state-highway corridors. Fixed on main, after this run",
        84: "Empty Overpass answer cached; corridor silently has no streets. Fixed on main by #91, after this run",
        111: "One wrong-county GPS crash in the box sends the no-GPS search to the wrong county (Marina). Open"}
H1 = Font(bold=True, size=14)
B = Font(bold=True)
HEAD = PatternFill("solid", fgColor="1F3A5F")
WHITE = Font(bold=True, color="FFFFFF")
WRAP = Alignment(wrap_text=True, vertical="top")
RESULT_FILL = {"pass": "C6EFCE", "warn": "FFEB9C", "fail": "FFC7CE", "untested": "D9D9D9"}


def git(*a) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True).stdout.strip()


def table(ws, name: str, header: list[str], rows: list[list], widths: dict[int, int] | None = None, start_row=1):
    for j, h in enumerate(header, 1):
        c = ws.cell(start_row, j, h)
        c.font, c.fill, c.alignment = WHITE, HEAD, Alignment(wrap_text=True, vertical="center")
    for i, r in enumerate(rows, start_row + 1):
        for j, v in enumerate(r, 1):
            ws.cell(i, j, v)
    end = start_row + max(1, len(rows))
    ref = f"A{start_row}:{get_column_letter(len(header))}{end}"
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(t)                                   # filters on every column
    ws.freeze_panes = ws.cell(start_row + 1, 2)
    ws.row_dimensions[start_row].height = 45
    for j in range(1, len(header) + 1):
        ws.column_dimensions[get_column_letter(j)].width = (widths or {}).get(j, 14)
    return end


def versions() -> list[str]:
    """Result folders (one per backend code version), oldest first."""
    ds = [d for d in (DATA / "results").iterdir() if d.is_dir() and any(d.glob("*.json"))]
    return [d.name for d in sorted(ds, key=lambda d: min(f.stat().st_mtime for f in d.glob("*.json")))]


def _oncor(r: dict) -> tuple:
    a = r.get("assignment") or {}
    return (a.get("intersection", 0) + a.get("segment", 0), a.get("unmatched", 0)) if a else (None, None)


def load_results(ver: str) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((DATA / "results" / ver).glob("*.json"))]


def cause(r: dict, agencies: dict) -> str:
    """One cause per city for the Problems sheet (code decides from the run's own fields)."""
    res = r["result"]
    if res == "pass":
        return ""
    if r.get("stage") == "corridor":
        return "No test corridor: " + r.get("reason", "")
    if r.get("stage") != "done":
        return f"App error at the {r.get('stage')} step"
    if r.get("silent_drops"):
        return "Silent drop: no-GPS reports naming the corridor and a study cross street not pulled"
    if not r.get("corridor_name"):
        return "App found no corridor street on the drawn line"
    if r.get("pulled", 0) == 0:
        return "0 crashes pulled" if r.get("independent_expected") else "No CCRS reports on the corridor"
    a = agencies.get(r.get("agency") or "")
    if a and a.get("drop_ratio") is not None and a["drop_ratio"] < 0.5:
        return "Agency stopped filing most reports in a recent year"
    if r.get("candidates") and r["review"] / r["candidates"] > 0.2:
        return ("Many crashes left for review (no GPS; the locator's suggestion is on a tier the user gate keeps "
                "for review, PR #16)")
    return "Low share located or placed"


def build(out_dir: Path, ver: str | None = None, before: str | None = None, record: bool = False) -> Path:
    vs = versions()
    ver = ver or vs[-1]
    before = before or (vs[-2] if len(vs) > 1 else None)
    results = load_results(ver)
    basis = next((r for r in results if r.get("settings")), {})
    agencies = json.loads((DATA / "agencies.json").read_text())
    ag_by = {a["ncic"]: a for a in agencies}
    tims = tims_compare.compare(DATA / "ccrs_mirror.sqlite", TIMS_DIR)
    today = dt.date.today().isoformat()
    wb = Workbook()

    cmeas = run_history.city_measures(results, [ROOT / "data" / "tester.sqlite",
                                                *sorted(DATA.glob("tester_worker*.sqlite"))], DATA / "ccrs_mirror.sqlite")
    # ---------------- 3 Cities ----------------
    wc = wb.active
    wc.title = "Cities"
    ch = ["City", "County code", "Police agency (NCIC)", "Agency share of city's crashes %", "CHP share %",
          "City crashes 2021-25 (CCRS)", "Test road (OSM)", "Corridor detected by app", "From", "To",
          "Study intersections", "Length ft", "Crashes pulled", "With GPS", "Placed (exact)", "Placed (other tiers)",
          "On corridor candidates", "Located or placed", "Located or placed %", "Sent for review", "Review %",
          "Excluded: side street / off stretch", "Excluded: freeway", "Excluded: outside buffer",
          "Excluded: outside study limits", "Excluded: other", "No-GPS reports expected (independent)",
          "Silent drops", "Example dropped Collision Ids", "Overpass empty retries", "Warnings", "Result", "Reason",
          "Cause", "Agency GPS % (2021-25)", "Agency worst year / 2016-19 median", "Result (run-1 rule)",
          "Independent street core (v2)", "Reports in the city naming the street (v2)",
          "No-GPS reports expected (independent v2)", "Silent drops (v2)", "Known issue", "Corridor inside its own city %",
          "Cities the corridor enters (city filter, #142)", "On corridor: located",
          "On corridor: no location", "On-corridor located % (v2)", "No location: no cross street",
          "No location: relaxed match held for review", "No-GPS reports expected (independent v3)",
          "Silent drops (v3)", "Silent drops (v4, offset-aware)", "v4 cleared (Collision Id: ft past the stretch end)",
          "Result (v4 rule)", "Corridor list", "GPS converted from DMS (#143)"]
    rows = []
    for r in sorted(results, key=lambda r: -r.get("crashes_5y", 0)):
        ex = Counter(r.get("excluded_by_rule") or {})
        tiers = r.get("placed_by_tier") or {}
        a = ag_by.get(r.get("agency") or "", {})
        cand = r.get("candidates") or 0
        asg_ = r.get("assignment") or {}
        on_, un_ = asg_.get("intersection", 0) + asg_.get("segment", 0), asg_.get("unmatched", 0)
        m_ = cmeas.get(f"{r['city']}|{r['county']}", {})
        rows.append([
            r["city"], int(r["county"]) if str(r["county"]).isdigit() else r["county"], r.get("agency"),
            r.get("agency_share"), r.get("chp_share"), r.get("crashes_5y"), (r.get("corridor") or {}).get("road"),
            r.get("corridor_name"), (r.get("ends") or [None, None])[0], (r.get("ends") or [None, None])[1],
            r.get("intersections"), r.get("length_ft"), r.get("pulled"), r.get("with_gps"), tiers.get("exact", 0),
            sum(v for k, v in tiers.items() if k != "exact"), cand, r.get("located"),
            round(r["located"] / cand, 3) if cand else None, r.get("review"),
            round(r["review"] / cand, 3) if cand and r.get("review") is not None else None,
            ex.pop("cross_street_not_on_corridor", 0), ex.pop("freeway", 0), ex.pop("outside_buffer", 0),
            ex.pop("outside_study_limits", 0), sum(ex.values()), r.get("independent_expected"), r.get("silent_drops"),
            ", ".join(r.get("silent_drop_ids") or []), r.get("overpass_empty_retries"),
            "; ".join(x for x in [r.get("warning"), r.get("error"), r.get("reason"),
                                  ("Parties table missing for " + ", ".join(map(str, r["parties_missing_years"])))
                                  if r.get("parties_missing_years") else None] if x),
            r["result"], r["result_reason"], cause(r, ag_by), a.get("gps_pct"), a.get("drop_ratio"),
            r.get("result_v1", r["result"]), r.get("independent_core_v2"), r.get("city_reports_naming_street_v2"),
            r.get("independent_expected_v2"), r.get("silent_drops_v2"), r.get("known_issue"),
            r.get("corridor_inside_own_city_pct"),
            None if "corridor_cities" not in r else ("FILTER OFF (OSM couldn't say)" if r["corridor_cities"] is None else
                                                     ", ".join(r["corridor_cities"]["cities"]) +
                                                     (" + unincorporated" if r["corridor_cities"]["outside"] else "")),
            on_, un_,
            round(on_ / (on_ + un_), 3) if on_ + un_ else None, m_.get("unplaced_no_cross"), m_.get("unplaced_relaxed"),
            r.get("independent_expected_v3"), r.get("silent_drops_v3"), r.get("silent_drops_v4"),
            ", ".join(f"{x['crash_id']}: {x['past_stretch_end_ft']}" for x in r.get("v4_cleared") or []) or None,
            r.get("result_v4"), r.get("corridor_list", "v1"), r.get("gps_dms_corrected")])
    n_city = table(wc, "Cities", ch, rows, {1: 20, 7: 24, 8: 24, 9: 20, 10: 20, 29: 24, 31: 40, 33: 40, 34: 40})
    for i in range(2, n_city + 1):
        for col in (19, 21, 47):
            wc.cell(i, col).number_format = "0%"
        res = wc.cell(i, 32).value
        if res in RESULT_FILL:
            wc.cell(i, 32).fill = PatternFill("solid", fgColor=RESULT_FILL[res])

    # ---------------- 4 Agencies ----------------
    wa = wb.create_sheet("Agencies")
    ah = ["NCIC", "Type", "Main city", "Cities served", "County code", "Crashes 2021-25", "Street crashes",
          "Freeway %", "GPS %", "Street GPS %", "No usable cross street %", "Cross street unreadable %",
          "Route-number names %", "House-address names %", "No suffix %", "Distance given %", "Feet typed as miles",
          "PDO %", "Amended (version > 1) %", "Same crash under 2+ Collision Ids", "Blank report numbers",
          "Most-used exact point: crashes", "Most-used point: streets", "Piled on points used 10+ times %",
          "Snapped GPS (report says > 250 ft) %", "Low-precision GPS %", "GPS outside own county %",
          "2016-19 median reports", "Worst year 2021-25", "Worst year / 2016-19", "Union City-type (no GPS)",
          "Reporting collapse"] + [f"Reports {y}" for y in range(2016, 2026)]
    arows = []
    for a in agencies:
        local = a["type"] == "local"
        arows.append([a["ncic"], a["type"], a["city"], a["n_cities"], int(a["county"]) if str(a["county"]).isdigit()
                      else a["county"], a["crashes"], a["street_crashes"], a["freeway_pct"], a["gps_pct"],
                      a["street_gps_pct"], a["sec_blank_pct"], a["sec_no_key_pct"], a["route_pct"], a["address_pct"],
                      a["no_suffix_pct"], a["offset_pct"], a["miles_gt2"], a["pdo_pct"], a["amended_pct"],
                      a["dup_same_crash"], a["blank_report_ids"], a["exact_point_n"],
                      "; ".join(f"{s} ({n})" for s, n in a.get("exact_point_roads") or []), a["piled_pct"],
                      a["snapped_far_pct"], a["low_precision_pct"], a["off_county_gps_pct"], a.get("base_2016_19"),
                      a.get("drop_year"), a.get("drop_ratio"),
                      "yes" if local and a["street_gps_pct"] < 20 and a["crashes"] >= 100 else "",
                      "yes" if local and a.get("drop_ratio") is not None and a["drop_ratio"] < 0.5
                      and (a.get("base_2016_19") or 0) >= 50 else ""]
                     + [a.get("years", {}).get(str(y), a.get("years", {}).get(y)) for y in range(2016, 2026)])
    n_ag = table(wa, "Agencies", ah, arows, {3: 20, 23: 36})

    # ---------------- 5 TIMS vs CCRS ----------------
    wt = wb.create_sheet("TIMS vs CCRS")
    th = ["County code", "County", "Year", "CCRS all crashes", "CCRS PDO (not in TIMS)", "CCRS F+I", "TIMS F+I",
          "F+I difference", "F+I difference %", "CCRS fatal crashes", "TIMS fatal", "CCRS serious-injury crashes",
          "TIMS serious", "CCRS F+I filed for places TIMS doesn't list", "Likely reason"]
    trows = [[r["county_code"], r["county"], r["year"], r["ccrs_total"], r["ccrs_pdo"], r["ccrs_fi"], r["tims_fi"],
              r["diff_fi"], r["diff_fi_pct"], r["ccrs_fatal"], r["tims_fatal"], r["ccrs_serious"], r["tims_serious"],
              r["ccrs_special_district_fi"], r["reason"]] for r in tims]
    n_tims = table(wt, "TimsCcrs", th, trows, {2: 16, 15: 70})
    # by county: totals over the final years 2021-2024 (2025 is provisional in both)
    wtc = wb.create_sheet("TIMS by county")
    agg: dict = {}
    for r in tims:
        if r["year"] <= 2024 and r.get("tims_fi") is not None:
            a_ = agg.setdefault((r["county_code"], r["county"]), [0, 0, 0])
            a_[0] += r["ccrs_fi"]
            a_[1] += r["tims_fi"]
            a_[2] += r["ccrs_special_district_fi"]
    n_tc = table(wtc, "TimsByCounty", ["County code", "County", "CCRS F+I 2021-24", "TIMS F+I 2021-24", "Difference",
                                       "Difference %", "CCRS F+I filed for places TIMS doesn't list"],
                 [[k, n, c_, t_, c_ - t_, round(100 * (c_ - t_) / t_, 2) if t_ else None, sd]
                  for (k, n), (c_, t_, sd) in sorted(agg.items())], {2: 16})

    # ---------------- 6 Problems ----------------
    wp = wb.create_sheet("Problems")
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        c = cause(r, ag_by)
        if c:
            groups[c].append(r)
    prows = []
    link = {"Silent drop": "#80, #83, #111", "App found no corridor": "#84", "No usable": "#82"}
    for c, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        ex = sorted(rs, key=lambda r: -r.get("crashes_5y", 0))[:4]
        prows.append([c, f'=COUNTIF(Cities!AH:AH,"{c}")', "; ".join(
            f"{r['city']} ({(r.get('corridor') or {}).get('road')}): {r['result_reason']}" for r in ex),
            next((v for k, v in link.items() if c.startswith(k)), "")])
    for num, title in BUGS.items():
        prows.append([f"Bug #{num}: {title}", None, "Found in the data scan or the run; failing test in "
                      "tests/tester/test_ccrs_agency_bugs.py", f"#{num}"])
    table(wp, "Problems", ["Cause", "Cities", "Examples (largest cities first)", "Bug issues"], prows,
          {1: 60, 2: 10, 3: 110, 4: 14})
    for row in wp.iter_rows(min_row=2):
        for c in row:
            c.alignment = WRAP

    # ---------------- 1 Summary ----------------
    ws = wb.create_sheet("Summary", 0)
    ws["A1"], ws["A1"].font = "CrashIQ statewide data test: every California city through tabs 1-2", H1
    meta = [("Test date", today), ("Test scripts (git commit)", git("rev-parse", "--short", "HEAD")),
            ("App code tested (commit / backend tree)", f"{basis.get('commit')} / {ver}"),
            ("Crash data", f"CCRS (CHP) on data.ca.gov, crash dates 2021-2025, mirror copied {basis.get('mirror_built')}"),
            ("Study settings", ", ".join(f"{k} {v}" for k, v in (basis.get("settings") or {}).items())),
            ("Comparison data", "TIMS SWITRS Summary (UC Berkeley SafeTREC), crashes as of Sep 15, 2026"),
            ("Street data", f"OpenStreetMap (ODbL): {basis.get('osm_source') or 'Overpass (live)'}")]
    for i, (k, v) in enumerate(meta, 3):
        ws.cell(i, 1, k).font = B
        ws.cell(i, 2, v)
    L = n_city
    has_v2 = any("silent_drops_v2" in r for r in results)
    has_v4 = any(r.get("silent_drops_v4") is not None for r in results)
    col_of = {h: get_column_letter(i) for i, h in enumerate(ch, 1)}
    sd_col = (col_of["Silent drops (v4, offset-aware)"] if has_v4 else "AO" if has_v2 else "AB")
    r4_col = col_of["Result (v4 rule)"]
    counts = [
        ("Agencies scanned", f"=COUNTA(Agencies!A2:A{n_ag})"),
        ("Cities in CCRS (incorporated)", f"=COUNTA(Cities!A2:A{L})"),
        ("Corridors run through the app", f'=COUNTIF(Cities!H2:H{L},"?*")'),
        ("Crashes pulled (all corridors)", f"=SUM(Cities!M2:M{L})"),
        ("Pass", f'=COUNTIF(Cities!AF2:AF{L},"pass")'),
        ("Warn", f'=COUNTIF(Cities!AF2:AF{L},"warn")'),
        ("Fail", f'=COUNTIF(Cities!AF2:AF{L},"fail")'),
        ("Untested (listed with reason)", f'=COUNTIF(Cities!AF2:AF{L},"untested")'),
        ("Pass (v4 check)", f'=COUNTIF(Cities!{r4_col}2:{r4_col}{L},"pass")'),
        ("Warn (v4 check)", f'=COUNTIF(Cities!{r4_col}2:{r4_col}{L},"warn")'),
        ("Fail (v4 check)", f'=COUNTIF(Cities!{r4_col}2:{r4_col}{L},"fail")'),
        ("Cities with silent drops", f'=COUNTIF(Cities!{sd_col}2:{sd_col}{L},">0")'),
        ("No-GPS reports silently dropped", f"=SUM(Cities!{sd_col}2:{sd_col}{L})"),
        ("Union City-type agencies (local, < 20% GPS)", f'=COUNTIF(Agencies!AE2:AE{n_ag},"yes")'),
        ("Agencies with a reporting collapse", f'=COUNTIF(Agencies!AF2:AF{n_ag},"yes")'),
        ("County-years where CCRS F+I is within 2% of TIMS", f'=COUNTIFS(\'TIMS vs CCRS\'!I2:I{n_tims},">=-2",\'TIMS vs CCRS\'!I2:I{n_tims},"<=2")'),
        ("County-years compared", f"=COUNT('TIMS vs CCRS'!I2:I{n_tims})"),
        ("Counties where CCRS F+I 2021-24 is within 2% of TIMS", f'=COUNTIFS(\'TIMS by county\'!F2:F{n_tc},">=-2",\'TIMS by county\'!F2:F{n_tc},"<=2")'),
        ("Counties compared", f"=COUNT('TIMS by county'!F2:F{n_tc})"),
    ]
    r0 = 11
    ws.cell(r0 - 1, 1, "Counts").font = B
    cell = {}
    for i, (k, f) in enumerate(counts, r0):
        ws.cell(i, 1, k)
        ws.cell(i, 2, f)
        cell[k] = f"B{i}"
    # results by county (formulas) for the chart
    cr = r0 + len(counts) + 2
    ws.cell(cr - 1, 1, "Results by county").font = B
    for j, h in enumerate(["County code", "pass", "warn", "fail", "untested"], 1):
        ws.cell(cr, j, h).font = B
    counties = sorted({row[1] for row in rows if isinstance(row[1], int)})
    for i, k in enumerate(counties, cr + 1):
        ws.cell(i, 1, k)
        for j, res in enumerate(["pass", "warn", "fail", "untested"], 2):
            ws.cell(i, j, f'=COUNTIFS(Cities!$B$2:$B${L},$A{i},Cities!$AF$2:$AF${L},"{res}")')
    ce = cr + len(counties)
    ch1 = BarChart()
    ch1.type, ch1.grouping, ch1.overlap = "col", "stacked", 100
    ch1.title, ch1.y_axis.title, ch1.x_axis.title = "Results by county", "Cities", "County code"
    ch1.add_data(Reference(ws, min_col=2, max_col=5, min_row=cr, max_row=ce), titles_from_data=True)
    ch1.set_categories(Reference(ws, min_col=1, min_row=cr + 1, max_row=ce))
    ch1.height, ch1.width = 9, 26
    ws.add_chart(ch1, "E3")
    # GPS rate distribution of local agencies
    gr = ce + 3
    ws.cell(gr - 1, 1, "Local agencies by GPS rate").font = B
    ws.cell(gr, 1, "GPS % band").font = B
    ws.cell(gr, 2, "Agencies").font = B
    bands = [(0, 10), (10, 20), (20, 40), (40, 60), (60, 80), (80, 90), (90, 101)]
    for i, (lo, hi) in enumerate(bands, gr + 1):
        ws.cell(i, 1, f"{lo}-{min(hi, 100)}%")
        ws.cell(i, 2, f'=COUNTIFS(Agencies!B2:B{n_ag},"local",Agencies!I2:I{n_ag},">={lo}",Agencies!I2:I{n_ag},"<{hi}")')
    ch2 = BarChart()
    ch2.title, ch2.y_axis.title, ch2.x_axis.title = "Local police agencies by share of reports with GPS", "Agencies", "GPS %"
    ch2.add_data(Reference(ws, min_col=2, min_row=gr, max_row=gr + len(bands)), titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=1, min_row=gr + 1, max_row=gr + len(bands)))
    ch2.height, ch2.width, ch2.legend = 8, 16, None
    ws.add_chart(ch2, "E22")
    # top failure reasons
    fr = gr + len(bands) + 3
    ws.cell(fr - 1, 1, "Warn and fail causes").font = B
    ws.cell(fr, 1, "Cause").font = B
    ws.cell(fr, 2, "Cities").font = B
    causes = sorted(groups, key=lambda c: -len(groups[c]))[:8]
    for i, c in enumerate(causes, fr + 1):
        ws.cell(i, 1, c)
        ws.cell(i, 2, f'=COUNTIF(Cities!AH2:AH{L},A{i})')
    if causes:
        ch3 = BarChart()
        ch3.type = "bar"
        ch3.title, ch3.legend = "Top warn/fail causes", None
        ch3.add_data(Reference(ws, min_col=2, min_row=fr, max_row=fr + len(causes)), titles_from_data=True)
        ch3.set_categories(Reference(ws, min_col=1, min_row=fr + 1, max_row=fr + len(causes)))
        ch3.height, ch3.width = 8, 26
        ws.add_chart(ch3, "E39")
    # conclusion: sentences are formulas quoting the cells above
    cc_ = fr + len(causes) + 3
    ws.cell(cc_ - 1, 1, "Conclusion").font = H1
    c = cell
    lines = [
        f'="Works: "&{c["Pass"]}&" of "&{c["Corridors run through the app"]}&" corridors pass (90%+ of crashes located by GPS or placed, nothing silently dropped). Source: Summary "&"{c["Pass"]}"&", Cities!AF."',
        f'="Does not work: "&{c["Fail"]}&" corridors fail and "&{c["Warn"]}&" warn. "&{c["Cities with silent drops"]}&" cities silently lose no-GPS reports ("&{c["No-GPS reports silently dropped"]}&" reports; Cities!{sd_col}). Causes: Problems sheet."',
        f'="Where it is at risk: "&{c["Union City-type agencies (local, < 20% GPS)"]}&" local police agencies record GPS on under 20% of reports (Agencies!AE), so every crash there depends on name matching."',
        f'="Hidden gap: "&{c["Agencies with a reporting collapse"]}&" local agencies filed less than half their 2016-19 report count in a year since 2021 (Agencies!AF, AD). TIMS shows the same gaps: it is built from the same CHP records, so it can\'t fill them."',
        f'="TIMS vs CCRS, fatal+injury only: within 2% in "&{c["Counties where CCRS F+I 2021-24 is within 2% of TIMS"]}&" of "&{c["Counties compared"]}&" counties (2021-24 totals, TIMS by county!F) and in "&{c["County-years where CCRS F+I is within 2% of TIMS"]}&" of "&{c["County-years compared"]}&" county-years (TIMS vs CCRS!I). Two different units: a county can match over four years while single years differ. CCRS adds property-damage-only crashes, which TIMS leaves out."',
        '="The plain-English conclusion of the whole test (what works, what doesn\'t, what to improve next) is on the Conclusion sheet."',
    ]
    for i, f in enumerate(lines, cc_):
        ws.cell(i, 1, f).alignment = WRAP
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=3)
        ws.row_dimensions[i].height = 48
    ws.column_dimensions["A"].width = 52
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 14

    # ---------------- 2 Method ----------------
    wm = wb.create_sheet("Method", 1)
    st = basis.get("settings") or {}
    vfile = DATA / "osm_validation.json"
    val = json.loads(vfile.read_text()) if vfile.exists() else {}
    osm_line = (f"Street data: {basis.get('osm_source') or 'Overpass (live)'}. " + (
        f"Checked against {val['corridors']} real Overpass answers for the same corridor queries: "
        f"{val['way_match_pct']}% of road ways match, the app detects the same corridor street on "
        f"{val['same_corridor_name']} of {val['corridors']} and the identical intersection list on "
        f"{val['same_intersection_list']} of {val['corridors']} (osm_local.validate)." if val else ""))
    method = [
        ("Street data (OSM)", "Overpass (overpass-api.de and its mirrors) rate-limited this machine during the run "
                              "(2026-10-20), so the whole run uses one dated Geofabrik extract "
                              "(california-latest.osm.pbf, MD5-checked, user OK for the download), loaded into SQLite "
                              "(osm_extract.py) and handed to the app through its own Overpass hook "
                              "(app.state.overpass, osm_local.py). The app's corridor query is answered the Overpass "
                              "way: road ways of the app's classes with any segment within 40 m of the drawn line, "
                              "in id order, with their nodes and node tags. " + osm_line),
        ("Basis of this run (PR #86)",
         f"App code: commit {basis.get('commit')} (backend tree {ver}). CCRS snapshot: local mirror copied from "
         f"data.ca.gov on {basis.get('mirror_built')}. Years: {st.get('from_year')}-{st.get('to_year')} by crash date "
         "(each CCRS year table holds only crashes dated in that year; checked). Preliminary records: kept and "
         "flagged, as the app does (69-135 per year statewide). Settings: influence radius "
         f"{st.get('radius_ft')} ft, buffer {st.get('buffer_ft')} ft, freeway crashes "
         f"{'included' if st.get('include_freeway') else 'excluded'}. Corridors: tests/statewide/"
         "corridors_frozen.json (exact lines); a rerun after fixes uses the same file, so before/after differ "
         "only in the code commit. Severity: the app's own (KABCO from InjuredWitnessPassengers)."),
        ("Purpose", "Run every incorporated California city through CrashIQ's data steps (tab 1: corridor and crash "
                    "pull; tab 2: placement and assignment) and measure where it works. Tabs 3-4 are out of scope."),
        ("What runs", "The app's own code, through its own API (FastAPI TestClient, in-process): create study → "
                      "PUT corridor (OSM detection) → POST crashes/pull (placement runs inside the pull) → GET "
                      "assignment. Nothing in backend/ was changed. App database: data/tester.sqlite (Tester's "
                      "copy) and data/statewide/tester_worker<n>.sqlite for the other parallel workers."),
        ("Crash data", "CCRS Crashes, Parties and InjuredWitnessPassengers 2021-2025 (the app's default window: last "
                       "5 complete years), copied once from data.ca.gov into a local SQLite mirror "
                       "(tests/statewide/ccrs_mirror.py) with the real column names and types. The app sends the "
                       "same SQL it sends to data.ca.gov; the mirror answers it. Parties 2025 is not published on "
                       "data.ca.gov (checked 2026-10-19), so 2025 crashes have no party data in any study."),
        ("Cities", "Every City Name with City Is Incorporated = True in CCRS 2021-2025. Police agency = the non-CHP "
                   "NCIC code with the most reports in that city."),
        ("Cities without an OSM boundary", "OSM has no boundary for Compton, and Rosemead's is tagged admin=8 "
                                           "instead of admin_level=8 (the loader accepts that typo). For a real city "
                                           "with no boundary, the corridor is picked inside the 2nd-98th percentile "
                                           "box of the city's own crash GPS (labelled on Cities). Places CCRS files "
                                           "as cities that aren't (parks, campuses, airports, harbors) stay untested."),
        ("Corridor per city", "The named OSM primary/secondary road (tertiary if none) with the most length inside "
                              "the city's OSM boundary (admin_level 8; San Francisco level 6). About 1 mile around "
                              "its middle, drawn along one carriageway's own geometry (shortest path over the road's "
                              "ways); windows that wind (> 1.35 x straight distance) are skipped. Code: corridors.py."),
        ("Independent check", "No-GPS reports in the city (CCRS City Name) whose one road contains the corridor "
                              "street and the other one of the app's study cross streets (letters and digits only). "
                              "Any such report the app didn't pull is a silent drop. v1 (run 1) took the street core "
                              "from the app's own names.py, so it shared the app's blind spots (#113). v2 (run 2 on) "
                              "uses its own core: leading directions and trailing suffixes dropped ('East Colorado "
                              "Boulevard' -> COLORADO); a report whose road states the opposite direction ('W COLORADO "
                              "BL' for East Colorado) isn't expected. v2 also counts every report in the city naming "
                              "the street. "
                              "Limit: a core can be shared by two streets (Van Ness / South Van Ness), which could flag "
                              "a drop that isn't one; drops are listed by Collision Id for checking."),
        ("Located or placed %", "Of crashes the pull kept as corridor candidates (not excluded at pull time): the "
                                "share with GPS or placed by the locator. Review % = share left unplaced."),
        ("Run-2 rule change (PM review of #112)", "0 crashes pulled is fail (suspected silent drop) when reports in "
                                                  "the city name the street (v2 count); untested only when none do. "
                                                  "Silent drops use the v2 check. The run-1 rule's result stays in "
                                                  "Cities 'Result (run-1 rule)', and Run history keeps v1 and v2 "
                                                  "counts in separate columns."),
        ("Pass / warn / fail", "Proposed in #73, for the user to confirm on this first report. Fail: any silent "
                               "drop, 0 crashes while CCRS has reports naming the corridor, the app found no "
                               "corridor street, or under 70% located/placed. Warn: 70-90% located/placed or more "
                               "than 20% sent for review. Pass: 90%+ and no silent drop. Untested: no corridor could "
                               "be drawn, or no CCRS report names it (reason listed)."),
        ("Agency scan", "All CCRS crash rows 2021-2025, latest report version per Collision Id, deleted reports out. "
                        "Measures per agency (NCIC): see Glossary. Yearly report counts 2016-2025 from data.ca.gov."),
        ("TIMS vs CCRS", "Fatal + injury only (TIMS has no PDO): F+I, fatal and serious-injury crashes by county and "
                         "year 2021-2025, by crash date. TIMS: SWITRS Summary tables, crashes as of Sep 15, 2026, "
                         "copied from the page in the signed-in browser panel (no file downloaded). CCRS: the same "
                         "mirror; one row per crash, deleted reports out, F+I = anyone killed or injured, fatal = "
                         "NumberKilled > 0, serious = any SuspectSerious/SevereInactive victim and not fatal. Where "
                         "the basis can't match: TIMS's snapshot (Sep 15) is older than the mirror; TIMS assigns "
                         "county from its own geocode while CCRS uses the report's County Code; TIMS doesn't list "
                         "crashes filed for state parks, campuses, airports and harbors; 2025 is provisional in both."),
        ("Excluded and why", "Unincorporated areas (no city corridor; CHP/sheriff crashes still enter through the "
                             "corridor box). PDO crashes are in CCRS but not TIMS, so they're shown, not compared."),
        ("Known limitations", "One corridor per city, so a pass means that road works, not every road. Streets "
                              "come from a local extract, not live Overpass; the match rate is above. The "
                              "mirror doesn't reproduce data.ca.gov's row caps or outages. Name-based checks can't "
                              "see crashes written with route numbers (#83) or wrong GPS (Agencies sheet)."),
        ("Reproduce", "python tests/statewide/ccrs_mirror.py is called by the runner; full run: "
                      "python tests/statewide/agency_scan.py && python tests/statewide/run_cities.py --shard 0/2 & "
                      "python tests/statewide/run_cities.py --shard 1/2; then python tests/statewide/build_workbook.py"
                      ". Cached reruns only redo cities whose backend code or corridor changed."),
    ]
    wm["A1"], wm["A1"].font = "Method", H1
    for i, (k, v) in enumerate(method, 3):
        wm.cell(i, 1, k).font = B
        wm.cell(i, 2, v).alignment = WRAP
        wm.cell(i, 1).alignment = WRAP
    wm.column_dimensions["A"].width = 24
    wm.column_dimensions["B"].width = 120

    # ---------------- 7 Glossary ----------------
    wg = wb.create_sheet("Glossary")
    gloss = [
        ("CCRS", "California Crash Reporting System, CHP's crash records on data.ca.gov (public domain)."),
        ("TIMS", "UC Berkeley SafeTREC's map and summaries of the same CHP records, fatal and injury crashes only."),
        ("NCIC", "Code of the reporting agency (police department, sheriff, CHP area). 9xxx = CHP."),
        ("F+I", "Fatal and injury crashes: anyone killed or injured."),
        ("PDO", "Property damage only: no one killed or injured."),
        ("GPS %", "Share of reports with a usable latitude/longitude."),
        ("No usable cross street %", "Cross street blank, NOT STATED, PRIVATE PROPERTY or 1-2 characters."),
        ("Route-number names %", "Road fields written as SR-1, RT 46, HWY 111, I-5 and similar."),
        ("Distance given %", "Reports giving a distance from the cross street."),
        ("Snapped GPS %", "Of reports the officer placed > 250 ft from the corner, the share whose GPS sits on a point "
                          "used by 10+ crashes: the GPS is the intersection, not the crash."),
        ("Same crash under 2+ Collision Ids", "Report numbers carried by 2+ Collision Ids with the same two roads."),
        ("Reporting collapse", "Worst year 2021-2025 below half the agency's 2016-2019 median report count."),
        ("Union City-type", "Local agency with under 20% GPS: every crash depends on street-name matching."),
        ("Located or placed", "Crash has GPS, or the app's locator placed it from the report's street names."),
        ("Sent for review", "Crash the app couldn't place automatically (location 'unmatched')."),
        ("Silent drop", "A no-GPS report naming the corridor and a study cross street that the app never pulled."),
        ("Excluded: side street / off stretch", "Pull rule #39: the cross street isn't one of the corridor's "
                                                "intersections (also the same street elsewhere in the county)."),
        ("Overpass empty retries", "Times OpenStreetMap's server answered with no streets and the harness asked again."),
    ]
    wg["A1"], wg["A1"].font = "Glossary", H1
    for i, (k, v) in enumerate(gloss, 3):
        wg.cell(i, 1, k).font = B
        wg.cell(i, 2, v).alignment = WRAP
    wg.column_dimensions["A"].width = 34
    wg.column_dimensions["B"].width = 110

    # ---------------- Fields ----------------
    wf = wb.create_sheet("Fields")
    fr_ = fields_check.check(DATA / "ccrs_mirror.sqlite", ROOT / "data" / "reference" / "ccrs_dictionary.json")
    table(wf, "Fields", ["Table", "Column", "App field", "Live value", "Rows 2021-25", "Share %", "In CHP dictionary",
                         "App mapping", "App maps this value", "Flag"],
          [[x["table"], x["field"], x["logical"], x["value"], x["rows"], x.get("share_pct"), x["in_dictionary"],
            x["app_map"], x["app_maps_value"], x["flag"]] for x in fr_], {2: 30, 4: 36, 8: 34, 10: 30})

    # ---------------- Run history ----------------
    city_list = json.loads((DATA / "cities.json").read_text())
    if record:   # completeness guard: an incomplete run raises run_history.IncompleteRun and is never recorded
        run_history.require_complete("frozen list v1", city_list, results)
        v2_list = HERE / "corridors_frozen_v2.json"
        v2_res = [json.loads(p.read_text()) for p in sorted((DATA / "results_corridors_v2" / ver).glob("*.json"))]
        if v2_list.exists():
            run_history.require_complete("corridor list v2", [c for c in json.loads(v2_list.read_text())["cities"]
                                                               if c.get("repicked")], v2_res)
        dbs_ = [ROOT / "data" / "tester.sqlite", *sorted(DATA.glob("tester_worker*.sqlite"))]
        run_history.record(results, tims, dbs_, DATA / "ccrs_mirror.sqlite", "tests/statewide/corridors_frozen.json")
        if v2_list.exists():
            run_history.record(run_history.series_v2(results, v2_res), tims, dbs_, DATA / "ccrs_mirror.sqlite",
                               "tests/statewide/corridors_frozen_v2.json", run_history.HISTORY_V2,
                               run_history.CITY_HISTORY_V2)
    rcell, hcell, acc_ref = {}, {}, None          # cells the Conclusion sheet quotes (filled below when present)
    wr = wb.create_sheet("Run history")
    hcols, hrows = run_history._read(run_history.HISTORY)
    if not hrows:
        wr["A1"] = ("No complete run recorded yet. A run is appended to tests/statewide/run_history.csv once every "
                    "city has a result (build_workbook.py --record); history is never overwritten.")
    else:
        conv = lambda v: (float(v) if re.fullmatch(r"-?\d+(\.\d+)?", v or "") else (v or None))  # noqa: E731
        end = table(wr, "RunHistory", hcols, [[conv(r.get(c)) for c in hcols] for r in hrows], {8: 30})
        hcell = {c_: f"'Run history'!{get_column_letter(j)}{end}" for j, c_ in enumerate(hcols, 1)}
        defs_at = end + 3
        wr.cell(defs_at, 1, "Measure definitions (a changed definition gets a new column, never a silent change)").font = B
        for i, (k, v) in enumerate(run_history.MEASURES.items(), defs_at + 1):
            wr.cell(i, 1, k)
            wr.cell(i, 2, v).alignment = WRAP
        groups_ = [("Coverage %", ["located_pct_v1", "review_pct_v1", "unplaced_pct_v1"]),
                   ("City results", ["pass_v1", "warn_v1", "fail_v1"]),
                   ("Mistakes found", ["silent_drops_v1", "double_counts_v1", "excluded_no_cross_street_v1"]),
                   ("TIMS counties within 2%", ["tims_counties_within_2pct_v1"])]
        for gi, (title, cols_) in enumerate(groups_):
            lc = LineChart()
            lc.title, lc.y_axis.title, lc.x_axis.title = title, title, "Run"
            for c_ in cols_:
                j = hcols.index(c_) + 1
                lc.add_data(Reference(wr, min_col=j, min_row=1, max_row=end), titles_from_data=True)
            lc.set_categories(Reference(wr, min_col=1, min_row=2, max_row=end))
            lc.height, lc.width = 7, 14
            wr.add_chart(lc, f"{get_column_letter(len(hcols) + 2 + (gi % 2) * 9)}{2 + (gi // 2) * 15}")
        # per-city result by run
        _, crows = run_history._read(run_history.CITY_HISTORY)
        runs_ = sorted({int(r["run"]) for r in crows})
        by = defaultdict(dict)
        for r in crows:
            by[(r["city"], r["county"])][int(r["run"])] = r["result"]
        wcr = wb.create_sheet("City by run")
        table(wcr, "CityByRun", ["City", "County code"] + [f"Run {n}" for n in runs_] + ["First run passed"],
              [[c, int(k) if str(k).isdigit() else k] + [v.get(n) for n in runs_] +
               [next((n for n in runs_ if v.get(n) == "pass"), None)] for (c, k), v in sorted(by.items())],
              {1: 22})

    cleared = [[r["city"], r["county"], x["crash_id"], x["cross_street"], x["direction"], x["offset_ft"],
                x["past_stretch_end_ft"]] for r in results for x in (r.get("v4_cleared") or [])]
    if any(r.get("silent_drops_v4") is not None for r in results):
        wv = wb.create_sheet("Silent drops v4 cleared")
        table(wv, "V4Cleared", ["City", "County code", "Collision Id", "Cross street (report)", "Direction",
                                "Offset ft (report)", "Past the stretch end ft (computed)"], cleared, {1: 22, 4: 26})

    v2cols, v2rows = run_history._read(run_history.HISTORY_V2)
    if v2rows:          # corridor list v2: its own sheet, never merged into Run history (v1)
        w2 = wb.create_sheet("Run history (corridors v2)")
        w2["A1"] = ("Second series (PM, PR #148): the corridor list with the corridors that lay mostly outside their "
                    "own city re-picked inside it. Its own baseline; don't compare these rows with Run history (v1).")
        conv2 = lambda v: (float(v) if re.fullmatch(r"-?\d+(\.\d+)?", v or "") else (v or None))  # noqa: E731
        hdr_row = 3
        for j, c_ in enumerate(v2cols, 1):
            w2.cell(hdr_row, j, c_).font = B
        for i, r_ in enumerate(v2rows, hdr_row + 1):
            for j, c_ in enumerate(v2cols, 1):
                w2.cell(i, j, conv2(r_.get(c_)))

    # ---------------- Reconciliation (run to run, crash by crash) ----------------
    if before:
        rc_file = DATA / f"reconcile_{before}_{ver}.json"
        if not rc_file.exists():
            rc_file.write_text(json.dumps(reconcile.reconcile(
                load_results(before), results,
                [ROOT / "data" / "tester.sqlite", *sorted(DATA.glob("tester_worker*.sqlite"))]), indent=1))
        rc = json.loads(rc_file.read_text())
        wrc = wb.create_sheet("Reconciliation")
        wrc["A1"], wrc["A1"].font = f"Reconciliation {before} -> {ver}: every crash in exactly one bucket", H1
        wrc["A2"] = (f"Like-for-like corridors only ({rc['cities']} cities with the same frozen line and a pull in both "
                     "runs). Crashes matched by Collision Id. 'Kept' = kept for the corridor (not excluded by a "
                     "rule); 'located' = kept with GPS or auto-placed. Bucket rules: tests/statewide/reconcile.py.")
        wrc["A2"].alignment = WRAP
        wrc.merge_cells("A2:G2")
        wrc.row_dimensions[2].height = 45
        hdr_r = 4
        bend = table(wrc, "Waterfall", ["Bucket", "What happened", "Cause", "Crashes", "Change in kept",
                                        "Change in located"],
                     [[b["bucket"], b["what"], b["cause"], b["crashes"], b["change_in_kept"], b["change_in_located"]]
                      for b in rc["buckets"]], {1: 18, 2: 52, 3: 34, 4: 12, 5: 14, 6: 14}, start_row=hdr_r)
        r0 = bend + 2
        k1, k2 = rc["kept"]
        l1, l2 = rc["located"]
        rowsx = [(f"Kept, {before}", k1), (f"Kept, {ver}", k2), (f"Located, {before}", l1), (f"Located, {ver}", l2),
                 ("Check: kept earlier + changes = kept later", f"=B{r0}+SUM(E{hdr_r + 1}:E{bend})=B{r0 + 1}"),
                 ("Check: located earlier + changes = located later", f"=B{r0 + 2}+SUM(F{hdr_r + 1}:F{bend})=B{r0 + 3}")]
        for i, (k_, v_) in enumerate(rowsx):
            wrc.cell(r0 + i, 1, k_).font = B
            wrc.cell(r0 + i, 2, v_)
        bi = {b["bucket"]: hdr_r + 1 + i for i, b in enumerate(rc["buckets"])}
        e0 = r0 + len(rowsx) + 1
        wrc.cell(e0, 1, "Evidence: where the earlier run's own assignment put the GPS crashes the later run no longer pulls").font = B
        for i, (k_, v_) in enumerate(rc["gps_no_longer_pulled_run1_assignment"].items(), e0 + 1):
            wrc.cell(i, 1, k_)
            wrc.cell(i, 2, v_)
        e1 = e0 + len(rc["gps_no_longer_pulled_run1_assignment"]) + 1
        cf = rc.get("located_removed_by_city_filter") or {}
        if cf.get("by_tier"):
            wrc.cell(e1, 1, "Evidence: located crashes the #142 city filter removed, by placement tier (reports filed "
                            "in another city with the same street pair)").font = B
            for t_, n_ in cf["by_tier"].items():
                e1 += 1
                wrc.cell(e1, 1, t_)
                wrc.cell(e1, 2, n_)
            for ex_ in cf.get("examples", []):
                e1 += 1
                wrc.cell(e1, 1, ex_).alignment = WRAP
            e1 += 1
        f0 = e1 + 1
        wrc.cell(f0, 1, "Located % on consistent denominators").font = H1
        sc = rc["same_crashes"]
        lines_ = [
            ("Same crashes kept in both runs", sc["kept_in_both"], None),
            (f"  located in {before}", sc["located_run1"], f"=B{f0 + 2}/B{f0 + 1}"),
            (f"  located in {ver}", sc["located_run2"], f"=B{f0 + 3}/B{f0 + 1}"),
            (f"{before} without GPS crashes it kept but never placed on the corridor (gps_margin bucket)",
             f"=B{r0 + 2}+F{bi['gps_margin']}", f"=B{f0 + 4}/(B{r0}+E{bi['gps_margin']})"),
            (f"{ver} without #121 junk and without no-cross-street reports kept for review (#94 policy)",
             f"=B{r0 + 3}-F{bi['junk_121']}-F{bi['no_cross_review']}",
             f"=B{f0 + 5}/(B{r0 + 1}-E{bi['junk_121']}-E{bi['no_cross_review']})"),
            (f"{ver} as measured (all kept crashes)", f"=B{r0 + 3}", f"=B{r0 + 3}/B{r0 + 1}"),
        ]
        for i, (k_, n_, pct_) in enumerate(lines_, f0 + 1):
            wrc.cell(i, 1, k_).alignment = WRAP
            wrc.cell(i, 2, n_)
            if pct_:
                wrc.cell(i, 3, pct_).number_format = "0.0%"
        wrc.cell(f0 + len(lines_) + 2, 1, (
            f'="Reading: on the "&TEXT(B{f0 + 1},"#,##0")&" crashes kept in both runs, located went from "&'
            f'TEXT(C{f0 + 2},"0.0%")&" to "&TEXT(C{f0 + 3},"0.0%")&". Changes in the as-measured figure come from the '
            f'buckets above (each crash in exactly one)."')).alignment = WRAP
        wrc.merge_cells(start_row=f0 + len(lines_) + 2, start_column=1, end_row=f0 + len(lines_) + 2, end_column=6)
        wrc.row_dimensions[f0 + len(lines_) + 2].height = 70
        wrc.column_dimensions["A"].width = 60
        hl = (f'="Headline (like for like): "&TEXT(Reconciliation!C{f0 + 3},"0.0%")&" of the same crashes located in '
              f'{ver} vs "&TEXT(Reconciliation!C{f0 + 2},"0.0%")&" in {before} · as measured: "&'
              f'TEXT(Reconciliation!C{f0 + 6},"0.0%")&" (all crashes kept for the corridor, Reconciliation sheet)"')
        ws["A2"] = hl
        rcell = {"kept_both": f"Reconciliation!B{f0 + 1}", "lfl_before": f"Reconciliation!C{f0 + 2}",
                 "lfl_after": f"Reconciliation!C{f0 + 3}", "as_measured": f"Reconciliation!C{f0 + 6}",
                 **{f"b_{k_}": f"Reconciliation!D{v_}" for k_, v_ in bi.items()},
                 **{f"bl_{k_}": f"Reconciliation!F{v_}" for k_, v_ in bi.items()}}
        ws["A2"].font = B
        wpc = wb.create_sheet("Reconciliation by city")
        table(wpc, "ReconcileCity", ["City", "County code"] + [b["bucket"] for b in rc["buckets"]],
              [[r["city"], int(r["county"])] + [r[b["bucket"]] for b in rc["buckets"]] for r in rc["per_city"]],
              {1: 22})

    # ---------------- Findings (#176, statewide Findings run on this run's code) ----------------
    fnd_file = DATA / f"findings_{ver}.json"
    if fnd_file.exists():
        fd = json.loads(fnd_file.read_text())
        sm = fd["summary"]
        wfd = wb.create_sheet("Findings")
        wfd["A1"], wfd["A1"].font = "Findings (tab 4): the code findings on every test corridor (#176)", H1
        wfd["A2"] = ("Each corridor's over-representation screen (T12, HSM excess-proportion test; binomial fallback "
                     "when no valid beta prior) and the findings code writes from it, run on this run's own backend "
                     "code and stored pulls. Every finding passes the app's validator or is rejected; a code finding "
                     "should never be rejected (its numbers all come from T12). tests/statewide/findings_run.py; the "
                     "T12 arithmetic itself is checked against raw rows in tests/tester/test_golden_t12.py.")
        wfd["A2"].alignment = WRAP
        wfd.merge_cells("A2:J2")
        wfd.row_dimensions[2].height = 60
        se = table(wfd, "FindingsSummary", ["Measure", "Value"], [
            ["Corridors screened", sm["cities"]], ["Locations screened", sm["locations_screened"]],
            ["T12 rows (location x crash type flagged)", sm["t12_rows"]],
            ["  of which binomial fallback (labelled a confidence, not a probability)", sm["t12_binomial"]],
            ["Corridors with at least one finding", sm["with_findings"]], ["Findings shown", sm["findings"]],
            ["Findings the validator rejected (expected 0; bug #179)", sm["rejected"]],
            ["Errors", sm["errors"]]], {1: 66, 2: 12}, start_row=4)
        cols_ = ["city", "county", "result", "locations_screened", "t12_rows", "t12_binomial", "t12_strong",
                 "findings_shown", "findings_rejected", "rejected_reasons"]
        table(wfd, "FindingsByCity", ["City", "County code", "Result", "Locations screened", "T12 rows",
                                      "Binomial fallback", "Strong", "Findings shown", "Rejected", "Why rejected"],
              [[x.get("city"), x.get("county"), x.get("result"), *[x.get(k) for k in cols_[3:9]],
                "; ".join(r for rs in x.get("rejected_reasons") or [] for r in rs) or None]
               for x in sorted(fd["cities"], key=lambda x: (-(x.get("findings_rejected") or 0),
                                                           -(x.get("findings_shown") or 0), x["city"]))],
              {1: 22, 10: 60}, start_row=se + 3)

    # ---------------- Statewide coverage (#199, user direction 2026-10-22): every CCRS crash in one of two bins --------
    cov_file = DATA / "coverage.json"
    if cov_file.exists():
        import coverage_out
        cv = json.loads(cov_file.read_text())
        ag_by_ = {a["ncic"]: a for a in agencies}
        hidden_ok = {a_["ncic"]: a_["exact_intersection_acc_pct"] for a_ in
                     json.loads((DATA / "accuracy_by_agency.json").read_text())
                     if (a_.get("gps_self_consistent_pct") or 0) >= 50 and a_.get("exact_intersection_acc_pct") is not None}

        def _acc_basis(ncic):
            if ncic == "3801":
                return "98.8% exact at the right intersection (San Francisco open data, claim C1)"
            if ncic in hidden_ok:
                return f"{hidden_ok[ncic]}% exact at the right intersection vs its own police GPS (#88, a lower bound)"
            return "can't verify (no truth source)"
        wsc = wb.create_sheet("Statewide coverage")
        b_ = cv["basis"]
        st_ = cv["statewide"][0]
        wsc["A1"], wsc["A1"].font = ("Statewide coverage: every CCRS crash 2021-2025, in one of two bins"
                                     + ("" if cv.get("complete") else " - PARTIAL, run still going")), H1
        wsc["A2"] = ("Bin 1 'on the map': police GPS that fits the report's roads (within "
                     f"{b_['gps_check_ft']:g} ft + the report's offset; degrees-minutes-seconds converted where the agency "
                     f"writes it), CrashIQ's placement from street names under its gate ({b_['gate']}), or the FARS point "
                     "for a fatal crash. Bin 2 'difficult': a likely match the gate holds, streets that meet in more than "
                     "one place, no cross street, or streets that don't meet on the map; the reason is kept per crash. "
                     f"Basis: CCRS mirror {b_['mirror']}, OSM {b_['osm']}, app code {b_['commit']}. On the map % is a share "
                     "of what CCRS holds, not of all crashes that happened: CCRS itself is incomplete (pain points 26-30; "
                     "Source completeness column). tests/statewide/coverage.py.")
        wsc["A2"].alignment = WRAP
        wsc.merge_cells("A2:N2")
        wsc.row_dimensions[2].height = 90
        he = table(wsc, "CoverageHeadline", ["Crashes", "In CCRS 2021-2025", "Bin 1: on the map %", "Bin 2: difficult %"],
                   [["All crashes", st_["crashes"], st_["on_map_pct"], st_["difficult_pct"]],
                    ["Fatal crashes", st_["fatal"], st_["fatal_on_map_pct"],
                     round(100 - st_["fatal_on_map_pct"], 1) if st_["fatal_on_map_pct"] is not None else None],
                    ["Fatal + serious injury (KSI)", st_["ksi"], st_["ksi_on_map_pct"],
                     round(100 - st_["ksi_on_map_pct"], 1) if st_["ksi_on_map_pct"] is not None else None]],
                   {1: 30, 2: 16, 3: 18, 4: 18}, start_row=4)
        acc_lines = [
            "Accuracy, by basis:",
            "- CrashIQ's exact street-name placement: 98.8% at the right intersection (95% low bound 98.3%, 3,632 crashes) "
            "on San Francisco's own geocoded records (claim C1, knowledge/claims.md).",
            "- Elsewhere, against an agency's own police GPS where that GPS is usable as truth (#88): pooled over those "
            f"agencies, {st_.get('accuracy', 'n/a')}; by district in the Caltrans district table, by agency in the "
            "Accuracy by agency sheet. Police GPS is noisy, so these are lower bounds. This covers city streets; freeways, "
            "state highways and county roads: can't verify.",
            "- Police GPS in bin 1 is checked for consistency with the report's roads, not graded for accuracy.",
            "- Every other agency: can't verify (no truth source).",
        ]
        for i_, t_ in enumerate(acc_lines, he + 2):
            wsc.cell(i_, 1, t_).alignment = WRAP
            wsc.merge_cells(start_row=i_, start_column=1, end_row=i_, end_column=10)
        r0_ = he + 2 + len(acc_lines) + 1
        src_rows = [["Police GPS, checked", st_["counts"].get("gps_usable", 0)],
                    ["Police GPS, converted from degrees-minutes-seconds", st_["counts"].get("gps_usable_dms", 0)],
                    ["CrashIQ from street names (exact, gate)", st_["counts"].get("placed_exact", 0)],
                    ["FARS point (fatal)", st_["counts"].get("placed_fars", 0)],
                    ["Review", st_["counts"].get("review", 0)], ["Can't place", st_["counts"].get("cant_place", 0)]]
        se_ = table(wsc, "CoverageSources", ["Where each crash's location comes from", "Crashes"], src_rows,
                    {1: 50, 2: 14}, start_row=r0_)
        re_ = table(wsc, "CoverageReasons", ["Bin 2 reason", "Crashes"],
                    [[k, v] for k, v in sorted(st_["difficult_by_reason"].items(), key=lambda kv: -kv[1])],
                    {1: 60, 2: 14}, start_row=se_ + 3)
        rcols = ["Crashes", "On the map %", "Difficult %", "Police GPS %", "CrashIQ placed %", "FARS %", "Review %",
                 "Can't place %", "Fatal", "Fatal on the map %", "KSI", "KSI on the map %"]
        rkeys = ["crashes", "on_map_pct", "difficult_pct", "police_gps_pct", "crashiq_placed_pct", "fars_pct",
                 "review_pct", "cant_place_pct", "fatal", "fatal_on_map_pct", "ksi", "ksi_on_map_pct"]
        last = re_
        for g_, title_, nm_ in (("district", "Caltrans district", "CoverageDistricts"),
                                ("road_type", "Road type", "CoverageRoadTypes"),
                                ("district_road_type", "District x road type", "CoverageDistrictRoad"),
                                ("county", "County", "CoverageCounties"), ("city", "City (CCRS city name)", "CoverageCities")):
            rows__ = cv[g_]
            if g_ == "district":
                rows__ = sorted(rows__, key=lambda r: int(r["name"].split()[-1]) if r["name"].split()[-1].isdigit() else 99)
            acc_ = g_ in ("district", "road_type")
            last = table(wsc, nm_, [title_] + rcols + (["Accuracy (hidden police GPS, #88)"] if acc_ else []),
                         [[r["name"]] + [r[k] for k in rkeys] + ([r.get("accuracy")] if acc_ else []) for r in rows__],
                         {1: 32, 14: 52} if acc_ else {1: 32}, start_row=last + 3)
        table(wsc, "CoverageAgencies", ["NCIC", "Agency", "Type"] + rcols + ["Source completeness", "Accuracy"],
              [[r["name"], r.get("agency_name"), r.get("agency_type")] + [r[k] for k in rkeys]
               + [coverage_out.completeness_note(r["name"], ag_by_.get(r["name"])),
                  _acc_basis(r["name"])] for r in cv["agency"]],
              {2: 22, 16: 50, 17: 46}, start_row=last + 3)

    # ---------------- Citywide coverage (#199): every non-freeway crash of every agency ----------------
    cw_file = DATA / "citywide.json"
    if cw_file.exists():
        cw = json.loads(cw_file.read_text())
        wcw = wb.create_sheet("Citywide coverage")
        bs = cw["basis"]
        wcw["A1"], wcw["A1"].font = ("Citywide coverage: of all crashes each police agency filed, how many reach the map "
                                     "(#199)" + ("" if cw.get("complete") else " - PARTIAL, run still going")), H1
        wcw["A2"] = (f"All non-freeway CCRS crashes 2021-2025 per agency (mirror {bs['mirror']}, OSM {bs['osm']}, app code "
                     f"{bs['commit']}). On the map = police GPS that fits the report's streets (within "
                     f"{bs['gps_check_ft']:g} ft + offset; degrees-minutes-seconds converted where the agency writes it) "
                     f"+ CrashIQ's own placement on the city's street map under its gate ({bs['gate']}), with FARS for "
                     "fatal crashes. Review = a likely match the gate holds, or streets that meet in more than one place. "
                     "Can't place = no cross street, or the named streets don't meet on the city's map. CHP areas and "
                     "agencies without an OSM city boundary: police GPS only. tests/statewide/citywide.py.")
        wcw["A2"].alignment = WRAP
        wcw.merge_cells("A2:N2")
        wcw.row_dimensions[2].height = 75
        hdr = ["NCIC", "Agency", "Type", "County code", "Crashes (non-freeway)", "Police GPS usable %",
               "CrashIQ placed %", "On the map %", "Review %", "Can't place %", "Not run %", "Fatal crashes",
               "Fatal on the map", "Accuracy", "Review reasons", "Can't-place reasons"]
        rows_ = [[a["ncic"], a["agency"], a["type"], a["county"], a["crashes"], a["police_gps_pct"],
                  a["crashiq_placed_pct"], a["on_map_pct"], a["review_pct"], a["cant_place_pct"], a["not_run_pct"],
                  (a.get("fatal") or {}).get("crashes", 0), (a.get("fatal") or {}).get("on_map", 0), a["accuracy"],
                  "; ".join(f"{k} {v}" for k, v in sorted(a["review_by_reason"].items(), key=lambda kv: -kv[1])),
                  "; ".join(f"{k} {v}" for k, v in sorted(a["cant_place_by_reason"].items(), key=lambda kv: -kv[1]))]
                 for a in sorted(cw["agencies"], key=lambda a: -a["crashes"])]
        ce = table(wcw, "CitywideCoverage", hdr, rows_, {2: 22, 14: 44, 15: 50, 16: 50}, start_row=4)
        local_ = [a for a in cw["agencies"] if a["type"] == "local" and a["crashes"] >= 200 and a["on_map_pct"] is not None
                  and not a.get("not_run_pct")]
        worst = sorted(local_, key=lambda a: a["on_map_pct"])[:25]
        we = table(wcw, "CitywideWorst25", ["Agency", "Crashes", "On the map %", "Police GPS %", "Review %",
                                            "Can't place %"],
                   [[a["agency"], a["crashes"], a["on_map_pct"], a["police_gps_pct"], a["review_pct"],
                     a["cant_place_pct"]] for a in worst], {1: 22}, start_row=ce + 3)
        value = sorted((a for a in local_ if (a["police_gps_pct"] or 0) < 20), key=lambda a: -a["on_map_pct"])[:25]
        table(wcw, "CitywideValueAdded", ["Agency (police GPS under 20%)", "Crashes", "Police GPS %",
                                          "CrashIQ placed %", "On the map %"],
              [[a["agency"], a["crashes"], a["police_gps_pct"], a["crashiq_placed_pct"], a["on_map_pct"]]
               for a in value], {1: 30}, start_row=we + 3)

    # ---------------- Fatal crashes before/after FARS (#178): this run vs the one before, same basis ----------------
    fo_now, fo_before = DATA / f"fatal_outcomes_{ver}.json", DATA / f"fatal_outcomes_{before}.json"
    if fo_now.exists() and fo_before.exists():
        fn, fb = json.loads(fo_now.read_text()), json.loads(fo_before.read_text())
        wfo = wb.create_sheet("Fatal before-after")
        wfo["A1"], wfo["A1"].font = f"Fatal crashes on the test corridors: {before} -> {ver} (#178, FARS #174)", H1
        wfo["A2"] = ("Every fatal crash the pull kept for a frozen-v1 corridor, by where each run's own code put it "
                     "(tests/statewide/fatal_outcomes.py). FARS points are treated like GPS (#174): within the "
                     "intersection radius or the corridor buffer they count; elsewhere on the report's roads they are "
                     "excluded as fars_off_corridor.")
        wfo["A2"].alignment = WRAP
        wfo.merge_cells("A2:F2")
        wfo.row_dimensions[2].height = 45
        keys = sorted(set(fn["fatal_outcomes"]) | set(fb["fatal_outcomes"]),
                      key=lambda k: (not k.startswith("placed"), k.startswith("unplaced"), k))
        oe = table(wfo, "FatalOutcomes", ["Outcome", f"Before ({before})", f"After ({ver})", "Change"],
                   [[k, fb["fatal_outcomes"].get(k, 0), fn["fatal_outcomes"].get(k, 0),
                     fn["fatal_outcomes"].get(k, 0) - fb["fatal_outcomes"].get(k, 0)] for k in keys],
                   {1: 40, 2: 16, 3: 16}, start_row=4)
        a_ = {(c["test_city"], c["crash_id"]): c for c in fb["crashes"]}
        b_ = {(c["test_city"], c["crash_id"]): c for c in fn["crashes"]}
        moves = Counter((a_[k]["outcome"] if k in a_ else "absent", b_[k]["outcome"] if k in b_ else "absent")
                        for k in set(a_) | set(b_))
        te = table(wfo, "FatalTransitions", ["Before", "After", "Fatal crashes"],
                   [[x, y, n] for (x, y), n in moves.most_common() if x != y], {1: 34, 2: 34}, start_row=oe + 3)
        ft_ = lambda p, q: round(math.hypot((p[0] - q[0]) * 364000, (p[1] - q[1]) * 364000 * math.cos(math.radians(p[0]))))
        table(wfo, "FatalLeftCorridor", ["City", "Collision Id", "Roads (report)", "Before", "FARS point vs before, ft",
                                         "After: off the corridor by, ft", "FARS case"],
              [[k[0], k[1], " / ".join(r or "" for r in a_[k]["roads"]), a_[k]["outcome"],
                ft_((a_[k]["lat"], a_[k]["lon"]), (b_[k]["lat"], b_[k]["lon"])), b_[k]["distance_ft"], b_[k]["fars_case"]]
               for k in sorted(a_) if a_[k]["outcome"].startswith("placed")
               and b_.get(k, {}).get("outcome") == "excluded_fars_off_corridor"], {1: 18, 3: 40, 4: 16}, start_row=te + 3)

    # ---------------- Fatal crashes (#166, measure only) ----------------
    fat_file = DATA / "fatal.json"
    if fat_file.exists():
        fa = json.loads(fat_file.read_text())
        wfa = wb.create_sheet("Fatal crashes")
        wfa["A1"], wfa["A1"].font = "Fatal crashes first: which ones CrashIQ can't place, and whether FARS can (#166)", H1
        wfa["A2"] = ("Measure only; nothing goes into the app. CCRS fatal crashes 2021-2025 (NumberKilled > 0). FARS: NHTSA "
                     f"California accident files {fa['basis']['fars_years'][0]}-{fa['basis']['fars_years'][-1]} (2025 not "
                     f"published). Link: county + date + time within {fa['basis']['link_minutes']} min + number killed, "
                     "roads as the tie-break; a FARS case is year + ST_CASE. A FARS point is usable when it is a real point "
                     f"(not an unknown code, not shared by 3+ crashes) and a road the report names runs within "
                     f"{fa['basis']['gps_check_ft']:g} ft (+ the report's offset) of it (local OSM). tests/statewide/fatal.py.")
        wfa["A2"].alignment = WRAP
        wfa.merge_cells("A2:F2")
        wfa.row_dimensions[2].height = 75
        lk, sn, co = fa["link"], fa["statewide_no_gps"], fa["corridor"]
        summary = [
            ("CCRS fatal crashes 2021-2025", fa["ccrs_fatal"]),
            ("  in FARS years (2021-2024)", lk["ccrs_fatal_in_fars_years"]),
            ("  linked to one FARS crash", lk.get("linked", 0)),
            ("  link rate %", lk["link_pct"]),
            ("  ambiguous (2+ FARS candidates the roads can't split)", lk.get("ambiguous", 0)),
            ("  not found in FARS", lk.get("unlinked", 0)),
            ("  FARS crashes linked to 2+ CCRS crashes (CCRS refilings)", lk["fars_crashes_linked_twice"]),
            ("Statewide: fatal crashes CCRS gives no GPS for", sn["count"]),
            ("  share of all fatal crashes %", sn["pct_of_fatal"]),
            ("  of those, no cross street either", sn["no_cross_street"]),
            *[(f"  {k}", v) for k, v in sorted(sn["fars"].items(), key=lambda kv: -kv[1])],
            ("Test corridors (latest run): fatal crashes kept", co["fatal_kept"]),
            ("  placed", co["placed"]),
            ("  unplaced", co["unplaced"]),
            *[(f"  unplaced: {k}", v) for k, v in co["unplaced_by_reason"].items()],
            *[(f"  unplaced, {k}", v) for k, v in co["unplaced_fars"].items()],
            ("Residue: no point from CCRS or FARS (for a later human-confirmed lookup)", fa["residue_count"]),
            ("  of which in 2021-2024 (FARS published)", fa["residue_in_fars_years"]),
            ("  of which 2025 (FARS 2025 not yet published)", fa["residue_by_year"].get("2025", 0)),
        ]
        fe = table(wfa, "FatalSummary", ["Measure", "Crashes"], [list(x) for x in summary], {1: 70, 2: 14}, start_row=4)
        ae = table(wfa, "FatalNoGpsByAgency", ["NCIC", "Agency", "Type", "Fatal crashes without GPS"],
                   [[a["ncic"], a["agency"], a["type"], a["fatal_no_gps"]] for a in sn["by_agency"]],
                   {1: 10, 2: 22}, start_row=fe + 3)
        table(wfa, "FatalCorridorUnplaced", ["City (test corridor)", "Collision Id", "Why unplaced", "FARS"],
              [[x["city"], x["crash_id"], x["reason"], x["fars"]] for x in co["unplaced_list"]], {1: 22, 3: 30, 4: 36},
              start_row=ae + 3)
        wre = wb.create_sheet("Fatal residue")
        with open(DATA / "fatal_residue.csv") as f_:
            rr = list(csv.reader(f_))
        table(wre, "FatalResidue", rr[0], rr[1:], {2: 18, 3: 18, 7: 30, 8: 30, 10: 36})

    # ---------------- Accuracy by agency (#88, hidden-GPS test) ----------------
    acc_file = DATA / "accuracy_by_agency.json"
    if acc_file.exists():
        acc = json.loads(acc_file.read_text())
        wac = wb.create_sheet("Accuracy by agency")
        cols_ = ["ncic", "city", "county", "status", "street_gps_pct", "gps_street_crashes", "sample",
                 "gps_self_consistent_pct", "review_pct"]
        for t_ in ("exact", "relaxed", "near", "fuzzy"):
            cols_ += [f"{t_}_share_pct", f"{t_}_intersection_acc_pct", f"{t_}_intersection_acc_low_pct",
                      f"{t_}_acc_consistent_pct", f"{t_}_acc_consistent_low_pct", f"{t_}_acc_pct",
                      f"{t_}_point_acc_with_distance_pct"]
        cols_.insert(8, "gps_usable_as_truth")
        for r in acc:
            sc = r.get("gps_self_consistent_pct")
            r["gps_usable_as_truth"] = None if sc is None else ("yes" if sc >= 50 else
                                                                "no: GPS disagrees with the report's own streets")
        a_end = table(wac, "AccuracyByAgency", cols_, [[r.get(c_) for c_ in cols_] for r in acc],
                      {2: 20, 4: 28, 9: 30})
        acc_ref = {k_: f"'Accuracy by agency'!{get_column_letter(cols_.index(k_) + 1)}2:"
                       f"{get_column_letter(cols_.index(k_) + 1)}{a_end}"
                   for k_ in ("exact_intersection_acc_pct", "status")}

    # ---------------- Sources for unplaced crashes (#88) ----------------
    ps_file = HERE / "portal_survey.json"
    if ps_file.exists():
        ps = json.loads(ps_file.read_text())
        wsu = wb.create_sheet("Sources for unplaced")
        wsu["A1"], wsu["A1"].font = "Sources for crashes CrashIQ can't place (measured only; nothing enters the app)", H1
        wsu["A2"] = ps["note"]
        wsu["A2"].alignment = WRAP
        wsu.merge_cells("A2:H2")
        wsu.row_dimensions[2].height = 45
        scol = ["agency", "ncic", "dataset", "link", "coords", "linked_pct", "no_gps_linked_pct", "terms", "notes", "url"]
        e_ = table(wsu, "OpenDataSources", scol, [[x.get(c_) for c_ in scol] for x in ps["sources"]],
                   {1: 22, 3: 36, 4: 36, 5: 30, 8: 40, 9: 50, 10: 40}, start_row=4)
        for row in wsu.iter_rows(min_row=5, max_row=e_):
            for c_ in row:
                c_.alignment = WRAP
        r_ = e_ + 2
        for k_, lbl in (("not_independent", "Not independent (copies of CHP/TIMS data)"), ("not_found", "No geocoded, "
                        "report-numbered dataset found"), ("to_check", "Candidates not yet confirmed")):
            wsu.cell(r_, 1, lbl).font = B
            wsu.cell(r_, 2, ", ".join(ps.get(k_, [])))
            r_ += 1
        wsu.cell(r_ + 1, 1, "TIMS geocodes for unplaced crashes").font = B
        wsu.cell(r_ + 1, 2, "Pending: the crash-by-crash TIMS match needs the two approved TIMS files on disk "
                            "(the browser can't save them, and moving them via the page was blocked). Reason groups "
                            "to report: no cross street (TIMS point is a guess), relaxed matches held by the gate, "
                            "other.").alignment = WRAP

    # ---------------- Before / after ----------------
    wba = wb.create_sheet("Before-after")
    if before:
        old = {(r["city"], r["county"]): r for r in load_results(before)}
        bah = ["City", "County code", "Same corridor line", f"Result before ({before}, run-1 rule)",
               f"Result after ({ver}, run-1 rule)", f"Result after ({ver}, run-2 rule)", "Pulled before",
               "Pulled after", "Located/placed before", "Located/placed after", "Silent drops before (v1)",
               "Silent drops after (v1)", "Silent drops after (v2)", "Changed (same rule)",
               "On corridor with location before", "On corridor without location before",
               "On corridor with location after", "On corridor without location after"]
        barows = []
        for r in sorted(results, key=lambda r: -r.get("crashes_5y", 0)):
            o = old.get((r["city"], r["county"]), {})
            same = (o.get("corridor") or {}).get("line") == (r.get("corridor") or {}).get("line")
            ob, oa = o.get("result_v1", o.get("result")), r.get("result_v1", r.get("result"))
            barows.append([r["city"], int(r["county"]), "yes" if same else "new corridor: not comparable", ob, oa,
                           r["result"], o.get("pulled"), r.get("pulled"), o.get("located"), r.get("located"),
                           o.get("silent_drops"), r.get("silent_drops"), r.get("silent_drops_v2"),
                           ("yes" if (ob, o.get("pulled"), o.get("silent_drops")) !=
                            (oa, r.get("pulled"), r.get("silent_drops")) else "") if same else "n/a",
                           *_oncor(o), *_oncor(r)])
        top = 16                               # like-for-like summary above the table, formulas only
        end_ba = table(wba, "BeforeAfter", bah, barows, {1: 22, 3: 26}, start_row=top)
        rng = lambda col: f"{col}{top + 1}:{col}{end_ba}"  # noqa: E731
        same_ok = f'{rng("C")},"yes"'
        wba["A1"], wba["A1"].font = f"Before / after: {before} -> {ver} (same mirror, OSM extract, settings)", H1
        wba["A2"] = ("Like for like = cities run on the identical frozen corridor line in both runs, compared under "
                     "the run-1 rule. Cities whose corridor was added after the freeze are counted separately.")
        rows_ = [("Comparable cities (same corridor line)", f'=COUNTIF({rng("C")},"yes")'),
                 ("Pass before (run-1 rule)", f'=COUNTIFS({same_ok},{rng("D")},"pass")'),
                 ("Pass after (run-1 rule)", f'=COUNTIFS({same_ok},{rng("E")},"pass")'),
                 ("Fail before (run-1 rule)", f'=COUNTIFS({same_ok},{rng("D")},"fail")'),
                 ("Fail after (run-1 rule)", f'=COUNTIFS({same_ok},{rng("E")},"fail")'),
                 ("Silent drops before (v1)", f'=SUMIFS({rng("K")},{same_ok})'),
                 ("Silent drops after (v1)", f'=SUMIFS({rng("L")},{same_ok})'),
                 ("On-corridor crashes with a location, before", f'=SUMIFS({rng("O")},{same_ok})'),
                 ("On-corridor crashes without a location, before", f'=SUMIFS({rng("P")},{same_ok})'),
                 ("On-corridor crashes with a location, after", f'=SUMIFS({rng("Q")},{same_ok})'),
                 ("On-corridor crashes without a location, after", f'=SUMIFS({rng("R")},{same_ok})'),
                 ("New corridors (not comparable)", f'=COUNTIF({rng("C")},"new corridor*")'),
                 ("  of which pass after (run-2 rule)",
                  f'=COUNTIFS({rng("C")},"new corridor*",{rng("F")},"pass")')]
        for i, (k_, f_) in enumerate(rows_, 3):
            wba.cell(i, 1, k_).font = B
            wba.cell(i, 2, f_)
    else:
        wba["A1"] = ("Before/after: filled in when the run is repeated after Engineering's fixes (#80-#84), on the "
                     "same frozen corridors, mirror and settings; only the app code commit differs.")

    # ---------------- Conclusion (plain English; every number is a formula over the sheets) ----------------
    wco = wb.create_sheet("Conclusion")
    wco["A1"], wco["A1"].font = "Conclusion: what the statewide test shows", H1
    wco["A2"] = ("Written for a reader who hasn't followed the runs. Every number below is an Excel formula that reads "
                 "it from the sheet named in brackets, so it always matches the data. 'Corridor' = a 1-mile test "
                 "stretch of a main road in each California city, run through the app's tabs 1-2.")
    wco["A2"].alignment = WRAP
    c = {k_: f"Summary!{v_}" for k_, v_ in cell.items()}      # Summary's cells, read from another sheet
    T = lambda ref, fmt="#,##0": f'TEXT({ref},"{fmt}")'  # noqa: E731
    v4 = c.get("Pass (v4 check)")
    works = [
        (f'="The app places crashes as well as before: of the "&{T(rcell["kept_both"])}&" crashes kept in both of the '
         f'last two runs, "&{T(rcell["lfl_after"], "0.0%")}&" are on the map now vs "&{T(rcell["lfl_before"], "0.0%")}'
         f'&" before (Reconciliation)."') if rcell else None,
        (f'="Corridors that pass: "&{v4}&" of "&{c["Corridors run through the app"]}&" locate 90% or more of '
         f'their crashes with no report missed ("&{c["Warn (v4 check)"]}&" warn, "&{c["Fail (v4 check)"]}&" fail; '
         f'Summary, Cities)."') if v4 else None,
        (f'="Of the crashes that count for a corridor, "&{T(hcell["on_corridor_located_pct_v2"], "0.0")}&"% have a '
         f'location (Run history, latest run)."') if "on_corridor_located_pct_v2" in hcell else None,
        (f'="Reports the app should have pulled but didn\'t (no GPS, naming the corridor and a study cross street, '
         f'found by the Tester\'s own independent search, check v4): "&{c["No-GPS reports silently dropped"]}&", in "&'
         f'{c["Cities with silent drops"]}&" cities (Cities; v2 and v3 counts beside it)."'),
        (f'="Reports from other cities are kept out, and unincorporated places are kept in: "&'
         f'{T(rcell["b_restored_147"])}&" reports filed under an unincorporated place\'s own name came back after '
         f'#147 (Reconciliation)."') if "b_restored_147" in rcell else None,
    ]
    sj = 'INDEX(Cities!AF:AF,MATCH("San Jose",Cities!A:A,0))'
    v2c = {c_: f"'Run history (corridors v2)'!{get_column_letter(j)}{3 + len(v2rows)}"
           for j, c_ in enumerate(v2cols, 1)} if v2rows else {}
    dms = get_column_letter(ch.index("GPS converted from DMS (#143)") + 1)
    works.append(f'="San Jose\'s GPS, which its police write as degrees-minutes-seconds, is now converted when it '
                 f'checks out against the report\'s streets (#143): "&TEXT(SUM(Cities!{dms}2:{dms}{L}),"#,##0")&" '
                 f'corridor crashes recovered statewide. San Jose\'s result: "&{sj}&" (Cities)."')
    works.append("The two street-name gaps found on corridor list v2 are fixed and re-checked: names with 'of' "
                 "(Avenue of Flags, #154) and numbered streets with a direction (East 4th Street, #155).")
    if "pass_v4" in v2c:
        works.append(f'="On corridor list v2 (the corridors that lay mostly outside their own city, re-picked inside '
                     f'it), "&{v2c["pass_v4"]}&" pass, "&{v2c["warn_v4"]}&" warn and "&{v2c["fail_v4"]}&" fail: its '
                     f'own baseline, not comparable with the runs above (Run history (corridors v2))."')
    fails = [
        (f'="Where it falls short most often: "&Summary!A{fr + 1}&" ("&Summary!B{fr + 1}&" cities; Summary, '
         f'Problems)."') if causes else None,
        (f'="Crashes left without a location, two kinds: "&{T(hcell["unplaced_no_cross_street_v2"])}&" reports give '
         f'no cross street, so they could be anywhere on the street; "&{T(hcell["unplaced_relaxed_held_v2"])}&" have '
         f'a likely match that the safety gate holds for a person to review (Run history)."')
        if "unplaced_relaxed_held_v2" in hcell else None,
        (f'="CrashIQ\'s counts agree with TIMS (built from the same CHP records) within 2% on fatal and injury '
         f'crashes 2021-24 in "&{c["Counties where CCRS F+I 2021-24 is within 2% of TIMS"]}&" of "&'
         f'{c["Counties compared"]}&" counties (TIMS by county). Agreement shows the records are processed '
         f'consistently, not that the source is complete: completeness is a separate issue (Agencies; pain points '
         f'26-27)."'),
        (f'="Some police agencies give the app little to work with: "&{c["Union City-type agencies (local, < 20% GPS)"]}'
         f'&" record GPS on under 20% of reports, and "&{c["Agencies with a reporting collapse"]}&" filed less than '
         f'half their usual reports in a recent year (Agencies). No map can fix missing reports."'),
        (f'="The \'exact\' match isn\'t always right: the median agency places "&'
         f'TEXT(MEDIAN({acc_ref["exact_intersection_acc_pct"]}),"0.0")&"% of exact matches at the correct '
         f'intersection when tested against their own hidden GPS (Accuracy by agency)."') if acc_ref else None,
    ]
    nxt = [
        (f'="1. Decide whether the safety gate may place \'relaxed\' matches on its own: "&'
         f'{T(hcell["unplaced_relaxed_held_v2"])}&" crashes wait on it (Run history), Dorris\'s among them (#155)."')
        if "unplaced_relaxed_held_v2" in hcell else None,
        "2. Use the report's own distance and direction from the cross street to place crashes, and city open "
        "data where it exists (Sources for unplaced: San Jose and Pasadena publish crash points linkable by report "
        "number; terms to check first).",
        "3. Report corridor list v2 (corridors re-picked inside their own city) alongside v1, so cities like "
        "Sacramento are tested on their own streets (Run history (corridors v2)).",
        "4. Finish the crash-by-crash TIMS match (#88) when the TIMS files are on disk, and extend the screen tests "
        "to drawing on the map and phone widths.",
    ]
    r_ = 4
    for title, lines_ in (("What works", works), ("What doesn't work yet", fails), ("What to improve next", nxt)):
        wco.cell(r_, 1, title).font = H1
        r_ += 1
        for f_ in [x for x in lines_ if x]:
            wco.cell(r_, 1, f_).alignment = WRAP
            wco.row_dimensions[r_].height = 48
            r_ += 1
        r_ += 1
    wco.column_dimensions["A"].width = 120

    order = ["Summary", "Method", "Cities", "Agencies", "Fields", "TIMS vs CCRS", "TIMS by county", "Problems", "Run history",
             "City by run", "Before-after", "Reconciliation", "Reconciliation by city", "Accuracy by agency",
             "Findings", "Citywide coverage", "Fatal before-after", "Fatal crashes", "Fatal residue", "Sources for unplaced", "Glossary"]
    order = [n for n in order if n in wb.sheetnames]
    order[0:0] = [n for n in ("Statewide coverage",) if n in wb.sheetnames]          # #199: first sheet
    order[order.index("Summary") + 1:order.index("Summary") + 1] = [n for n in ("Conclusion",) if n in wb.sheetnames]
    wb._sheets = [wb[n] for n in order] + [w for w in wb._sheets if w.title not in order]   # never drop a sheet
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"CrashIQ-statewide-test-{today}.xlsx"
    wb.save(out)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", help="backend tree (results folder) to report; default: newest")
    ap.add_argument("--before", help="earlier version for the Before-after sheet; default: the one before")
    ap.add_argument("--record", action="store_true", help="append this (complete) run to run_history.csv")
    a = ap.parse_args()
    print(build(ROOT / "reports" / "testing", a.version, a.before, a.record))
