"""Build data/reference/caltrans_rate_groups.csv from Caltrans' "2024 Basic Average Crash Rate Table" (#287 part 1;
user decision 2026-10-29, docs/03 #294). Deterministic: pdftotext -layout, one regex per row, no typing by hand.

Usage: python scripts/extract_caltrans_rate_groups.py <2024-crash-data-on-cshwy-book-v3-a11y.pdf> <out.csv>

The book (2024 Crash Data on California State Highways) prints the table on pages 83-90: highways H01-H67 (83-85),
intersections I01-I31 (86-87), ramps R01-R80 (88-90). Printed page = PDF page - 3.
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys

PAGES = range(86, 94)                    # PDF pages of printed pages 83-90
COUNTS = {"H": 67, "I": 31, "R": 80}
ROW = re.compile(r"^\s*([HIR])\s+(\d{2})\s+(\d+\.\d+)\s+(\d+\.\d+)\s*([/*])?\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(.+?)"
                 r"\s+(\d+\.\d+)\s+(\d+\.\d+)\s*$")
AREAS = {"RURAL", "SUBURBAN", "URBAN", "ALL*"}
TERRAIN = re.compile(r"^(FLAT|ROLL|MTN|ROLL/MTN|<=\d{4,}|>\d{4,})$")
SPEED = re.compile(r"^(<=|>=|<|>)?\d{2}(-\d{2})?$")
COLS = ["group", "kind", "base_rate", "adt_factor", "adt_op", "pct_fatal", "pct_injury", "pct_fi", "type",
        "terrain_or_adt", "design_speed", "control", "ramp_areas", "on_off", "area", "cost_fi_k", "cost_all_k",
        "printed_page"]


def parse_row(line: str, printed_page: int) -> dict | None:
    m = ROW.match(line)
    if not m:
        return None
    k, n, base, fac, op, fat, inj, fi, mid, c_fi, c_all = m.groups()
    chunks = re.split(r"\s{2,}", mid.strip())
    r = {"group": f"{k}{n}", "kind": {"H": "highway", "I": "intersection", "R": "ramp"}[k], "base_rate": base,
         "adt_factor": fac, "adt_op": op or "", "pct_fatal": fat, "pct_injury": inj, "pct_fi": fi, "type": chunks[0],
         "terrain_or_adt": "", "design_speed": "", "control": "", "ramp_areas": "", "on_off": "", "area": "",
         "cost_fi_k": c_fi, "cost_all_k": c_all, "printed_page": printed_page}
    rest = chunks[1:]
    if k == "H":                         # terrain or ADT, design speed, area; "45-55 SUBURBAN" has one space
        for tok in (t for c in rest for t in c.split(" ")):
            if tok in AREAS:
                r["area"] = tok
            elif TERRAIN.match(tok):
                r["terrain_or_adt"] = tok
            elif SPEED.match(tok):
                r["design_speed"] = tok
            else:
                raise ValueError(f"{r['group']}: unknown field {tok!r}")
    elif k == "I":                       # intersection type, control type, area
        r["control"], r["area"] = rest
    else:                                # ramp type, ramp areas, on/off, area
        r["ramp_areas"], r["on_off"], r["area"] = rest
    if not r["area"]:
        raise ValueError(f"{r['group']}: no area")
    return r


def extract(pdf: str) -> list[dict]:
    rows = []
    for p in PAGES:
        text = subprocess.run(["pdftotext", "-layout", "-f", str(p), "-l", str(p), pdf, "-"], check=True,
                              capture_output=True, text=True).stdout
        rows += [r for line in text.splitlines() if (r := parse_row(line, p - 3))]
    check(rows)
    return rows


def check(rows: list[dict]) -> None:
    """Every group once and in order, and each row's fatal + injury percentages add to its F+I percentage."""
    for k, n in COUNTS.items():
        got = [r["group"] for r in rows if r["group"][0] == k]
        if got != [f"{k}{i:02d}" for i in range(1, n + 1)]:
            raise ValueError(f"{k} groups: expected {k}01-{k}{n:02d}, got {len(got)}")
    for r in rows:
        if abs(float(r["pct_fatal"]) + float(r["pct_injury"]) - float(r["pct_fi"])) > 0.051:
            raise ValueError(f"{r['group']}: percentages don't add up")
        if float(r["adt_factor"]) and not r["adt_op"]:
            raise ValueError(f"{r['group']}: an ADT factor without '/' or '*'")


if __name__ == "__main__":
    rows = extract(sys.argv[1])
    with open(sys.argv[2], "w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rate groups -> {sys.argv[2]}")
