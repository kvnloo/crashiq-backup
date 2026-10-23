"""#219 outputs: the agency GPS profile write-up, tracker CSVs, and the re-check summary. Every number is read from
gps_profile.json, gps_piles.json and gps_recheck.json; this file only arranges and labels them.

Run: python tests/statewide/gps_report.py   (writes data/statewide/gps_profile.md and data/statewide/tracker/gps_*.csv)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
OUT = DATA / "tracker"
LABEL = {"fits": "fits the report's streets", "snapped": "at the named intersection, report states an offset",
         "dms": "degrees-minutes-seconds (wrong format)", "pile": "shared default / dispatch point",
         "low_precision": "2 decimals or fewer", "far_off": "more than a mile from the named roads",
         "off_other": "other: off the roads, within a mile"}
MIN_GPS = 500


def agency_label(a: dict, ag: dict) -> str:
    x = ag.get(a["ncic"]) or {}
    if (x.get("n_cities") or 1) > 3:
        return f"{a['ncic']} {x.get('city')} + {x.get('n_cities') - 1} more city names ({x.get('type')})"
    return f"{a['ncic']} {x.get('city') or ''} ({x.get('type')})"


def main() -> None:
    gp = json.loads((DATA / "gps_profile.json").read_text())
    pl = json.loads((DATA / "gps_piles.json").read_text())
    rc = json.loads((DATA / "gps_recheck.json").read_text())
    ag = {a["ncic"]: a for a in json.loads((DATA / "agencies.json").read_text())}
    cls, st = gp["classes"], gp["statewide"]
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "gps_classes.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "label", "crashes", "pct"])
        for c in cls:
            w.writerow([c, LABEL[c], st[c], st[f"{c}_pct"]])
    with open(OUT / "gps_years.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "gps_crashes"] + [f"{c}_pct" for c in cls])
        for y, v in gp["by_year"].items():
            w.writerow([y, v["gps_crashes"]] + [v[f"{c}_pct"] for c in cls])
    big = [a for a in gp["agencies"] if a["gps_crashes"] >= MIN_GPS]
    with open(OUT / "gps_agencies.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ncic", "agency", "gps_crashes", "gps_share_pct"] + [f"{c}_pct" for c in cls])
        for a in sorted(big, key=lambda a: a["fits_pct"]):
            w.writerow([a["ncic"], agency_label(a, ag), a["gps_crashes"], a["gps_share_pct"]] + [a[f"{c}_pct"] for c in cls])
    md = [f"# Agency GPS quality profile (#219), {gp['basis']}", "",
          f"{st['gps_crashes']:,} crashes with police GPS, each in one class:", "", "| Class | Crashes | Share |", "|---|---|---|"]
    md += [f"| {LABEL[c]} | {st[c]:,} | {st[f'{c}_pct']}% |" for c in cls]
    md += ["", "## By year", "", "| Year | GPS crashes | " + " | ".join(LABEL[c] for c in cls) + " |",
           "|" + "---|" * (len(cls) + 2)]
    md += [f"| {y} | {v['gps_crashes']:,} | " + " | ".join(f"{v[f'{c}_pct']}%" for c in cls) + " |"
           for y, v in gp["by_year"].items()]
    for c, title in (("snapped", "at the named intersection while the report states an offset"),
                     ("far_off", "more than a mile from the named roads"), ("pile", "on shared default points"),
                     ("dms", "in degrees-minutes-seconds"), ("off_other", "off the roads within a mile")):
        md += ["", f"## Agencies with most GPS {title} (at least {MIN_GPS} GPS crashes)", "",
               "| Agency | GPS crashes | Share |", "|---|---|---|"]
        md += [f"| {agency_label(a, ag)} | {a['gps_crashes']:,} | {a[f'{c}_pct']}% |"
               for a in sorted(big, key=lambda a: -(a[f"{c}_pct"] or 0))[:10]]
    md += ["", "## Shared default / dispatch points (pooled over agencies; #218 rule)", "",
           f"Rule: {pl['thresholds']}. {len(pl['piles'])} points, {pl['pile_crashes']:,} crashes.", "",
           "| Point | Crashes | Agencies | Street pairs | Years | Nearest streets | Miles from city centre |",
           "|---|---|---|---|---|---|---|"]
    md += [f"| {p['lat']}, {p['lon']} | {p['crashes']} | {p['n_agencies']} | {p['street_pairs']} | "
           f"{', '.join(map(str, p['by_year']))} | {'; '.join(p['nearest_streets'][:2]) or '(no named street within ~500 ft)'} | "
           f"{p['miles_from_city_centre']} ({p['nearest_city_centre']}) |" for p in pl["piles"][:20]]
    md += ["", "## Re-check: \"GPS right, names wrong\"?", "",
           f"{rc['cases']} difficult crashes whose police GPS is off the report's roads but within a mile of them "
           f"({rc['by_source'].get('audit', 0)} from the #211 audit sample, {rc['by_source'].get('random', 0)} random). "
           "Evidence: the streets meeting at the GPS point and their similarity to the report's names, the distance to "
           "each named road, the stated offset, and whether the point is a default point (tests/statewide/gps_recheck.py).",
           "", "| Class | All cases | Random sample |", "|---|---|---|"]
    md += [f"| {k} | {v} | {rc['classes_random_sample'].get(k, 0)} |" for k, v in rc["classes"].items()]
    (DATA / "gps_profile.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:30]))


if __name__ == "__main__":
    main()
