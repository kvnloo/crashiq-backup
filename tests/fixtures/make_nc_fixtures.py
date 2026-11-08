"""Record the NC source fixture (tests/fixtures/nc_sources.json): a few real ArcGIS pages from each open NC layer,
keyed by layer URL, replayed offline by tests/test_source_nc.py. Re-run only to refresh (needs network):
    PYTHONPATH=backend python tests/fixtures/make_nc_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

from crashiq.sources import nc_durham, nc_ncdot, nc_raleigh
from crashiq.sources.nc_arcgis import _get

OUT = Path(__file__).parent / "nc_sources.json"


def page(layer: str, where: str, oid: str, n: int) -> dict:
    return _get(layer + "/query", {"where": where, "outFields": "*", "orderByFields": oid, "resultRecordCount": n,
                                   "outSR": 4326, "f": "json"})


def main() -> None:
    # Raleigh 2025: a mix of intersection ("At"), offset ("From"), house-address and injury crashes
    crashes = page(nc_raleigh.CRASHES, "Crash_Date_Year=2025 AND (type_a_injury>0 OR killed>0)",
                   "OBJECTID", 6)
    crashes["features"] += page(nc_raleigh.CRASHES, "Crash_Date_Year=2025", "OBJECTID", 24)["features"]
    crashes["features"] += page(nc_raleigh.CRASHES, "Crash_Date_Year=2024 AND Crash_Date_Month_Num=7", "OBJECTID",
                                5)["features"]                    # before the Oct 2024 time-zone change
    keys = ",".join(str(f["attributes"]["key_crash"]) for f in crashes["features"])
    persons = page(nc_raleigh.PERSONS, f"key_crash IN ({keys})", "OBJECTID", 300)
    out = {
        nc_raleigh.CRASHES: crashes,
        nc_raleigh.PERSONS: persons,
        nc_ncdot.KA: page(nc_ncdot.KA, "1=1", "FID", 25),
        nc_ncdot.NON_MOTORIST: page(nc_ncdot.NON_MOTORIST, "CrashYear=2025", "FID", 25),
        nc_durham.LAYER: page(nc_durham.LAYER, "Date >= DATE '2025-12-30'", "OBJECTID_1", 40),
    }
    for v in out.values():                     # trim what the readers never read: layer metadata, empty attributes
        v.pop("fields", None)
        for f in v["features"]:
            f["attributes"] = {k: x for k, x in f["attributes"].items() if x not in (None, "", " ")}
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(OUT, OUT.stat().st_size, {k.rsplit("/", 3)[-3]: len(v["features"]) for k, v in out.items()})


if __name__ == "__main__":
    main()
