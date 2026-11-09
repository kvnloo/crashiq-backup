"""Build the synthetic TxDOT CRIS public-extract fixture (tests/fixtures/tx_cris/) from the published spec.

The column headers of every file come from TxDOT's spec workbook (each file's sheet, "Column Header" column), in the
spec's order and spelling; the rows are invented, using the value formats seen in real CRIS copies (dates
MM/DD/YYYY, times "02:50 PM", flags Y/N, codes from the spec's lookup sheets). No real crash is in the fixture.
Run (needs the spec xlsx, ~2 MB, not committed):
  curl -o /tmp/spec.xlsx https://www.txdot.gov/content/dam/docs/division/trf/crash-records/public-extract-file-specification.xlsx
  ~/Desktop/Crash/.venv/bin/python tests/fixtures/make_tx_cris_fixture.py /tmp/spec.xlsx
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import openpyxl

OUT = Path(__file__).parent / "tx_cris"
SHEETS = {"crash": "Crash File Specification", "unit": "Unit File Specification",
          "person": "Person File Specification", "primaryperson": "PrimaryPerson File Spec."}
LOOKUPS = ("COLLSN_LKP", "LIGHT_COND_LKP", "WTHR_COND_LKP", "SURF_COND_LKP", "CITY_LKP", "CNTY_LKP")
NAME = "extract_public_20261107120000_{}_20250101-20251231_DALLAS.csv"

BASE = {"Crash_Date": "03/14/2025", "Crash_Time": "02:50 PM", "Rpt_CRIS_Cnty_ID": "57", "Cnty_ID": "57",
        "Rpt_City_ID": "107", "City_ID": "107", "Txdot_Rptable_Fl": "Y", "Private_Dr_Fl": "N", "Onsys_Fl": "N",
        "Located_Fl": "Y", "Wthr_Cond_ID": "11", "Light_Cond_ID": "1", "Surf_Cond_ID": "1", "Death_Cnt": "0",
        "Tot_Injry_Cnt": "0"}
CRASHES = [
    # off-system intersection: street + intersecting street, TxDOT-located, suspected serious injury
    {"Crash_ID": "90000001", "Rpt_Rdwy_Sys_ID": "19", "Rpt_Block_Num": "1900", "Rpt_Street_Pfx": "E",
     "Rpt_Street_Name": "BELT LINE", "Rpt_Street_Sfx": "RD", "At_Intrsct_Fl": "Y", "Rpt_Sec_Rdwy_Sys_ID": "19",
     "Rpt_Sec_Street_Pfx": "S", "Rpt_Sec_Street_Name": "HIGHLAND", "Rpt_Sec_Street_Sfx": "DR",
     "Latitude": "32.58983430", "Longitude": "-96.93730255", "Street_Name": "E BELT LINE RD", "Street_Nbr": "1900",
     "Crash_Sev_ID": "1", "Tot_Injry_Cnt": "2", "Sus_Serious_Injry_Cnt": "1", "FHE_Collsn_ID": "14"},
    # on-system interstate, officer names no street: highway + reference marker offset; fatal pedestrian at night
    {"Crash_ID": "90000002", "Crash_Time": "11:05 PM", "Rpt_Rdwy_Sys_ID": "1", "Rpt_Hwy_Num": "35",
     "Rpt_Hwy_Sfx": "E", "Rpt_Street_Name": "NOT REPORTED", "Rpt_Sec_Rdwy_Sys_ID": "19",
     "Rpt_Sec_Street_Name": "COMMERCE", "Rpt_Sec_Street_Sfx": "ST", "At_Intrsct_Fl": "N",
     "Rpt_Ref_Mark_Nbr": "430", "Rpt_Ref_Mark_Offset_Amt": "0.3", "Rpt_Ref_Mark_Dist_Uom": "MI",
     "Rpt_Ref_Mark_Dir": "N", "Onsys_Fl": "Y", "Hwy_Sys": "IH", "Hwy_Nbr": "0035", "Hwy_Sfx": "E",
     "Control": "196", "Section": "3", "Milepoint": "2.345", "Dfo": "430.112", "Ref_Mark_Nbr": "0430",
     "Ref_Mark_Displ": "0.312", "Street_Name": "IH0035E", "Func_Sys_ID": "11", "Adt_Curnt_Amt": "145111",
     "Adt_Curnt_Year": "2023", "Latitude": "32.77538919", "Longitude": "-96.81186160", "Light_Cond_ID": "4",
     "Crash_Sev_ID": "4", "Crash_Fatal_Fl": "Y", "Death_Cnt": "1", "FHE_Collsn_ID": "5"},
    # the TxDOT locator could not place it; the officer's own GPS is used; 150 ft west of the intersection
    {"Crash_ID": "90000003", "Crash_Date": "07/04/2025", "Crash_Time": "08:15 AM", "Rpt_Rdwy_Sys_ID": "19",
     "Rpt_Street_Name": "WALNUT", "Rpt_Street_Sfx": "ST", "Rpt_Sec_Rdwy_Sys_ID": "19",
     "Rpt_Sec_Street_Name": "GREENVILLE", "Rpt_Sec_Street_Sfx": "AVE", "At_Intrsct_Fl": "N",
     "Rpt_Ref_Mark_Offset_Amt": "150", "Rpt_Ref_Mark_Dist_Uom": "FT", "Rpt_Ref_Mark_Dir": "W",
     "Located_Fl": "N", "Rpt_Latitude": "32.92307423", "Rpt_Longitude": "-96.74025258", "Crash_Sev_ID": "3",
     "Tot_Injry_Cnt": "1", "FHE_Collsn_ID": "20"},
    # parking lot, no coordinates at all, nobody hurt
    {"Crash_ID": "90000004", "Rpt_Rdwy_Sys_ID": "19", "Rpt_Street_Name": "TOWN SQUARE", "Rpt_Street_Sfx": "BLVD",
     "Private_Dr_Fl": "Y", "Txdot_Rptable_Fl": "N", "Located_Fl": "N", "Crash_Sev_ID": "5"},
    # severity unknown on the crash and every person
    {"Crash_ID": "90000005", "Rpt_Rdwy_Sys_ID": "19", "Rpt_Street_Name": "ROYAL", "Rpt_Street_Sfx": "LN",
     "Latitude": "32.89509424", "Longitude": "-96.88170901", "Crash_Sev_ID": "0"},
    # 0/0 coordinates (not a place) and no person rows: the crash-level code decides (suspected minor)
    {"Crash_ID": "90000006", "Rpt_Rdwy_Sys_ID": "19", "Rpt_Street_Name": "LAKE JUNE", "Rpt_Street_Sfx": "RD",
     "Rpt_Sec_Street_Name": "AVIS", "Rpt_Sec_Street_Sfx": "ST", "Latitude": "0", "Longitude": "0",
     "Crash_Sev_ID": "2", "Tot_Injry_Cnt": "1"},
]
UNITS = [("90000001", "1", "1", "104"), ("90000001", "2", "1", "69"), ("90000002", "1", "1", "30"),
         ("90000002", "2", "4", ""), ("90000003", "1", "1", "71"), ("90000004", "1", "1", "104"),
         ("90000005", "1", "1", "104"), ("90000006", "1", "1", "103")]
# (crash, unit, person, person type, injury severity id, primary?)
PERSONS = [("90000001", "1", "1", "1", "1", True), ("90000001", "1", "2", "2", "2", False),
           ("90000001", "2", "1", "1", "5", True), ("90000002", "1", "1", "1", "5", True),
           ("90000002", "2", "1", "4", "4", True), ("90000003", "1", "1", "5", "3", True),
           ("90000004", "1", "1", "1", "5", True), ("90000005", "1", "1", "1", "0", True)]


def headers(wb, sheet: str) -> list[str]:
    rows = list(wb[sheet].iter_rows(values_only=True))
    start = next(i for i, r in enumerate(rows) if r and r[0] == "Column Header") + 1
    # the spec's crash sheet has one blank-looking header ("`", Report Date) - keep the spec's text as is
    return [str(r[0]).strip() for r in rows[start:] if r and r[0] not in (None, "")]


def write(kind: str, cols: list[str], rows: list[dict]) -> None:
    with (OUT / NAME.format(kind)).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def main(spec: Path) -> None:
    wb = openpyxl.load_workbook(spec, read_only=True)
    OUT.mkdir(exist_ok=True)
    write("crash", headers(wb, SHEETS["crash"]), [{**BASE, **c} for c in CRASHES])
    write("unit", headers(wb, SHEETS["unit"]), [{"Crash_ID": c, "Unit_Nbr": u, "Unit_Desc_ID": d,
                                                 "Veh_Body_Styl_ID": b, "Veh_HNR_Fl": "N"} for c, u, d, b in UNITS])
    for kind, primary in (("primaryperson", True), ("person", False)):
        write(kind, headers(wb, SHEETS[kind]),
              [{"Crash_ID": c, "Unit_Nbr": u, "Prsn_Nbr": p, "Prsn_Type_ID": t, "Prsn_Injry_Sev_ID": s}
               for c, u, p, t, s, pr in PERSONS if pr == primary])
    used = {c.get("FHE_Collsn_ID") for c in CRASHES} | {"1", "4", "11", "107", "57"}
    lk = []
    for sheet in LOOKUPS:
        rows = list(wb[sheet].iter_rows(values_only=True))
        for r in rows[1:]:
            if r and r[0] is not None and str(r[0]) in used and (len(r) < 4 or str(r[3] or "").startswith("9999")):
                lk.append({"ColumnName": rows[0][0], "ID": r[0], "Description": r[1]})
    write("lookup", ["ColumnName", "ID", "Description"], lk)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
