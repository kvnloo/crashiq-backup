"""Run 8b citywide sample (Engineering's ask on #218): #218 rule 1 on EVERY crash with police GPS of the agencies
where GPS is most often snapped to the intersection while the report states an offset (#219: Santa Ana, Vacaville,
South Gate, Glendale). For each crash the GPS check passes (the run-8a coverage: gps_usable), the app's own pieces
decide: the meeting point of the two named roads within gps.json snap_ft of the GPS (the stated intersection), a
stated offset over offset_min_ft in a cardinal direction, and crashiq.gps_rules._along_named_road for the new point.
Reported per agency: snapped with an offset, moved, kept (no named road runs that way), and how far the point moved
(beyond 250 ft it leaves the intersection's influence area: a segment crash in a corridor study).

Run: python tests/statewide/run8b_snapped.py   (writes data/statewide/run8b_snapped.json)
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
AGENCIES = {"3019": "Santa Ana", "4806": "Vacaville", "1969": "South Gate", "1925": "Glendale"}


def main() -> None:
    from crashiq import gps_rules, locate, names, osm

    import citywide as cw
    import corridors
    import osm_local

    cfg = gps_rules.CONFIG
    with open(DATA / "coverage_crashes_r8b.csv") as f:
        usable = {r["collision_id"] for r in csv.DictReader(f) if r["outcome"] == "gps_usable" and r["agency"] in AGENCIES}
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    res = {}
    for ag, city in AGENCIES.items():
        net = osm.Network(osm_local.network_in_box(local, bounds[corridors.norm_city(city)]["rel"]))
        c_ = Counter()
        dist = []
        seen = set()
        for c in cw.mirror_rows(con, "NCIC Code", ag):
            cid = str(c["crash_id"])
            if cid not in usable or cid in seen:
                continue
            seen.add(cid)
            c_["gps_fits"] += 1
            off, d = c.get("offset_ft") or 0.0, str(c.get("offset_dir") or "").strip()[:1].upper()
            kp, ks = names.street_key(c.get("primary_road")), names.street_key(c.get("secondary_road"))
            a = locate._keys_matching(net, kp) or locate._same_core_keys(net, kp) if kp else []
            bb = [s for s in ((locate._keys_matching(net, ks) or locate._same_core_keys(net, ks)) if ks else []) if s not in a]
            meet = locate._shared_nodes(net, a, bb) if a and bb else []
            near = [n for n in meet if osm.metres(net.coord[n], (c["lat"], c["lon"])) <= cfg["snap_ft"] * locate.FT]
            if not near:
                continue
            c_["at_named_intersection"] += 1
            if off <= cfg["offset_min_ft"] or d not in gps_rules.CARDINAL:
                continue
            c_["snapped_with_offset"] += 1
            node = min(near, key=lambda n: osm.metres(net.coord[n], (c["lat"], c["lon"])))
            pt = gps_rules._along_named_road(net, node, c, off, d)
            if pt is None:
                c_["kept_no_road_that_way"] += 1
                continue
            c_["moved"] += 1
            m_ft = osm.metres((c["lat"], c["lon"]), pt) / locate.FT
            dist.append(m_ft)
            c_["moved_beyond_250ft"] += m_ft > 250
        dist.sort()
        res[f"{ag} {city}"] = {**c_, "median_move_ft": round(dist[len(dist) // 2]) if dist else None,
                               "p90_move_ft": round(dist[int(len(dist) * 0.9)]) if dist else None}
        print(ag, city, res[f"{ag} {city}"], flush=True)
    (DATA / "run8b_snapped.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
