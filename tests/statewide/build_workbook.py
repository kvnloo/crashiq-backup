"""Write the statewide test workbook (#73) from the cached run outputs. No network; reruns are free.

Inputs:  data/statewide/results/*.json (run_cities.py), data/statewide/agencies.json (agency_scan.py),
         the CCRS mirror + data/cache/statewide/tims/ (tims_compare.py).
Output:  reports/testing/CrashIQ-statewide-test-<date>.xlsx

Every number on Summary is an Excel formula over the data sheets, and the Conclusion sentences are formulas that
quote those cells, so no number is typed by hand (CLAUDE.md: code computes every number).
"""

from __future__ import annotations

import datetime as dt
import json
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
        return "Many crashes left for review (no GPS, not auto-placed)"
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
          "No-GPS reports expected (independent v2)", "Silent drops (v2)"]
    rows = []
    for r in sorted(results, key=lambda r: -r.get("crashes_5y", 0)):
        ex = Counter(r.get("excluded_by_rule") or {})
        tiers = r.get("placed_by_tier") or {}
        a = ag_by.get(r.get("agency") or "", {})
        cand = r.get("candidates") or 0
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
            r.get("independent_expected_v2"), r.get("silent_drops_v2")])
    n_city = table(wc, "Cities", ch, rows, {1: 20, 7: 24, 8: 24, 9: 20, 10: 20, 29: 24, 31: 40, 33: 40, 34: 40})
    for i in range(2, n_city + 1):
        for col in (19, 21):
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
    sd_col = "AO" if has_v2 else "AB"
    counts = [
        ("Agencies scanned", f"=COUNTA(Agencies!A2:A{n_ag})"),
        ("Cities in CCRS (incorporated)", f"=COUNTA(Cities!A2:A{L})"),
        ("Corridors run through the app", f'=COUNTIF(Cities!H2:H{L},"?*")'),
        ("Crashes pulled (all corridors)", f"=SUM(Cities!M2:M{L})"),
        ("Pass", f'=COUNTIF(Cities!AF2:AF{L},"pass")'),
        ("Warn", f'=COUNTIF(Cities!AF2:AF{L},"warn")'),
        ("Fail", f'=COUNTIF(Cities!AF2:AF{L},"fail")'),
        ("Untested (listed with reason)", f'=COUNTIF(Cities!AF2:AF{L},"untested")'),
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
        '="Every severity number is wrong until bug #79 is fixed: real CCRS injury codes map to U, so serious injuries (A) are never counted. Problems sheet lists all bugs."',
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
                      "copy) and data/statewide/tester_worker1.sqlite for the second parallel worker."),
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
                              "Boulevard' -> COLORADO). v2 also counts every report in the city naming the street. "
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
    complete = len(results) >= len(city_list)
    if record and complete:
        run_history.record(results, tims, [ROOT / "data" / "tester.sqlite", DATA / "tester_worker1.sqlite"],
                           DATA / "ccrs_mirror.sqlite", "tests/statewide/corridors_frozen.json")
    wr = wb.create_sheet("Run history")
    hcols, hrows = run_history._read(run_history.HISTORY)
    if not hrows:
        wr["A1"] = ("No complete run recorded yet. A run is appended to tests/statewide/run_history.csv once every "
                    "city has a result (build_workbook.py --record); history is never overwritten.")
    else:
        conv = lambda v: (float(v) if re.fullmatch(r"-?\d+(\.\d+)?", v or "") else (v or None))  # noqa: E731
        end = table(wr, "RunHistory", hcols, [[conv(r.get(c)) for c in hcols] for r in hrows], {8: 30})
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

    # ---------------- Before / after ----------------
    wba = wb.create_sheet("Before-after")
    if before:
        old = {(r["city"], r["county"]): r for r in load_results(before)}
        bah = ["City", "County code", "Same corridor line", f"Result before ({before})", f"Result after ({ver})",
               "Pulled before", "Pulled after", "Located/placed before", "Located/placed after", "Silent drops before",
               "Silent drops after", "Changed"]
        barows = []
        for r in sorted(results, key=lambda r: -r.get("crashes_5y", 0)):
            o = old.get((r["city"], r["county"]), {})
            same = (o.get("corridor") or {}).get("line") == (r.get("corridor") or {}).get("line")
            barows.append([r["city"], int(r["county"]), "yes" if same else "NO", o.get("result"), r["result"],
                           o.get("pulled"), r.get("pulled"), o.get("located"), r.get("located"),
                           o.get("silent_drops"), r.get("silent_drops"),
                           "yes" if (o.get("result"), o.get("pulled"), o.get("silent_drops")) !=
                           (r["result"], r.get("pulled"), r.get("silent_drops")) else ""])
        table(wba, "BeforeAfter", bah, barows)
    else:
        wba["A1"] = ("Before/after: filled in when the run is repeated after Engineering's fixes (#80-#84), on the "
                     "same frozen corridors, mirror and settings; only the app code commit differs.")

    order = ["Summary", "Method", "Cities", "Agencies", "Fields", "TIMS vs CCRS", "TIMS by county", "Problems", "Run history",
             "City by run", "Before-after", "Glossary"]
    order = [n for n in order if n in wb.sheetnames]
    wb._sheets = [wb[n] for n in order]
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
