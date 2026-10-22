"""Outputs of the statewide coverage test (#199): small CSVs for the tracker and the county outline for its map.
Reads data/statewide/coverage.json (coverage.py); writes data/statewide/tracker/coverage_*.csv and ca_counties.json.
Every number comes from coverage.json; this file only arranges and labels them.

Run: python tests/statewide/coverage_out.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import citywide_out

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
OUT = DATA / "tracker"

# Source completeness beside coverage (#199): what CCRS itself is known to miss, from measurements in this repo.
COMPLETENESS = {
    "1942": "CCRS holds 67-77% of LAPD's own crash count (pain point 5)",
    "4313": "CCRS holds 44% of San Jose's own 2024 crashes (pain point 27)",
}


def completeness_note(ncic: str, agency: dict | None) -> str:
    if ncic in COMPLETENESS:
        return COMPLETENESS[ncic]
    a = agency or {}
    if a.get("type") == "local" and a.get("drop_ratio") is not None and a["drop_ratio"] < 0.5 and \
            (a.get("base_2016_19") or 0) >= 50:
        return f"filed under half its 2016-19 reports in {a.get('drop_year')} (Agencies sheet)"
    return ""


def _write(name: str, cols: list[str], rows: list[dict]) -> None:
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    cv = json.loads((DATA / "coverage.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["name", "crashes", "on_map_pct", "difficult_pct", "police_gps_pct", "crashiq_placed_pct", "fars_pct",
            "review_pct", "cant_place_pct", "fatal", "fatal_on_map_pct", "ksi", "ksi_on_map_pct"]
    s = cv["statewide"][0]
    head = [{"measure": "all crashes", "crashes": s["crashes"], "on_map_pct": s["on_map_pct"],
             "difficult_pct": s["difficult_pct"]},
            {"measure": "fatal crashes", "crashes": s["fatal"], "on_map_pct": s["fatal_on_map_pct"],
             "difficult_pct": round(100 - s["fatal_on_map_pct"], 1) if s["fatal_on_map_pct"] is not None else None},
            {"measure": "fatal + serious injury (KSI)", "crashes": s["ksi"], "on_map_pct": s["ksi_on_map_pct"],
             "difficult_pct": round(100 - s["ksi_on_map_pct"], 1) if s["ksi_on_map_pct"] is not None else None}]
    _write("coverage_headline.csv", ["measure", "crashes", "on_map_pct", "difficult_pct"], head)
    _write("coverage_sources.csv", ["source", "crashes", "pct"],
           [{"source": lbl, "crashes": s["counts"].get(k, 0), "pct": round(100 * s["counts"].get(k, 0) / s["crashes"], 1)}
            for k, lbl in (("gps_usable", "Police GPS, checked against the report's roads"),
                           ("gps_usable_dms", "Police GPS converted from degrees-minutes-seconds"),
                           ("placed_exact", "CrashIQ placed from street names (exact, under the gate)"),
                           ("placed_fars", "FARS point (fatal crashes)"),
                           ("review", "Review: a likely match held, or streets meeting twice"),
                           ("cant_place", "Can't place: no cross street, or streets that don't meet"))])
    reasons = s["difficult_by_reason"]
    _write("coverage_reasons.csv", ["reason", "crashes"],
           [{"reason": k, "crashes": v} for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])])
    by_name = lambda g: sorted(cv[g], key=lambda r: r["name"])    # noqa: E731
    _write("coverage_districts.csv", cols, sorted(cv["district"], key=lambda r: int(r["name"].split()[-1])
                                                  if r["name"].split()[-1].isdigit() else 99))
    _write("coverage_road_types.csv", cols, cv["road_type"])
    _write("coverage_counties.csv", cols, by_name("county"))
    where = citywide_out.centroids(ROOT / "data" / "osm" / "ca_osm.sqlite")
    import corridors
    cities = []
    for r in cv["city"]:
        ll = where.get(corridors.norm_city(r["name"]))
        cities.append({**r, "lat": ll[0] if ll else None, "lon": ll[1] if ll else None})
    _write("coverage_cities.csv", cols + ["lat", "lon"], cities)
    (OUT / "ca_counties.json").write_text(json.dumps(citywide_out.counties(ROOT / "data" / "osm" / "ca_osm.sqlite"),
                                                     separators=(",", ":")))
    print(f"coverage outputs ({'complete' if cv.get('complete') else 'PARTIAL'}) -> {OUT}")


if __name__ == "__main__":
    main()
