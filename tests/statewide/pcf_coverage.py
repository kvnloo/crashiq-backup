"""How much of CCRS the PCF crosswalk (data/reference/pcf_categories.csv) covers.

CCRS publishes only the violation text, written many ways: 'VC 22350', '22350', 'VC 21658(A)', '21453A', '23152(a)',
sometimes words ('UNSAFE BACKING') or nothing. This parses the text to (section, subsection) the way the crosswalk is
keyed and counts every CCRS crash into one outcome: mapped / unknown (CHP gives 00) / split / section not in the
table / text not a section / blank. Engineering's loader should reproduce these numbers.

Run: python tests/statewide/pcf_coverage.py   (needs the local CCRS mirror)
"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECTION = re.compile(r"^(?:C?VC\s*)?(\d{2,5})\s*(?:[.(]?\s*([A-Z0-9])[A-Z0-9]*\s*\)?)?\s*$")
SUFFIX = re.compile(r"\s+C?VC\.?$")       # '22107 CVC', '22350 VC' (the code written after the section)


def parse(text: str | None) -> tuple[str, str] | None | str:
    """(section, subsection) | 'blank' | None (text that isn't a section)."""
    t = re.sub(r"\s+", " ", str(text or "").strip().upper())
    if not t:
        return "blank"
    m = SECTION.match(SUFFIX.sub("", t))
    return (m.group(1), m.group(2) or "") if m else None


def coverage(mirror_db: Path, crosswalk: Path, years=(2021, 2022, 2023, 2024)) -> dict:
    table = {(r["section"], r["subsection"]): r["status"] for r in csv.DictReader(crosswalk.open())
             if r["key_type"] == "section"}
    con = sqlite3.connect(mirror_db)
    out = {"all": Counter(), "fatal_injury": Counter()}
    unparsed = Counter()
    for rid, y in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'"):
        if y not in years:
            continue
        q = (f'SELECT "Primary Collision Factor Violation", COALESCE("NumberKilled",0) + COALESCE("NumberInjured",0) '
             f'FROM "{rid}" WHERE COALESCE("IsDeleted", \'\') <> \'True\'')
        for text, ki in con.execute(q):
            p = parse(text)
            if p == "blank":
                k = "blank (no violation text)"
            elif p is None:
                k = "text, not a section"
                unparsed[str(text).strip().upper()] += 1
            else:
                k = {"mapped": "mapped", "unknown": "unknown (CHP assigns 00)", "split": "split (listed)"}.get(
                    table.get(p), "section not in the crosswalk")
            out["all"][k] += 1
            if ki > 0:
                out["fatal_injury"][k] += 1
    con.close()
    return {"counts": {k: dict(v) for k, v in out.items()}, "top_unparsed": unparsed.most_common(15)}


if __name__ == "__main__":
    res = coverage(ROOT / "data" / "statewide" / "ccrs_mirror.sqlite", ROOT / "data" / "reference" / "pcf_categories.csv")
    for scope, c in res["counts"].items():
        tot = sum(c.values())
        print(scope, tot)
        for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
            print(f"  {k:32} {v:8}  {100 * v / tot:5.1f}%")
    print("top text that isn't a section:", res["top_unparsed"])
