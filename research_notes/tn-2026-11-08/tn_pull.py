"""Tennessee: pull Davidson County through the reader's own calls (TDOT 2024, TDOSHS + Metro Nashville 2025), measure
them, check that Metro's no-injury crashes are not already in the state's fatal+injury layer, compare TDOT's and
TDOSHS's 2024 injury crashes, and record the test fixture.
    PYTHONPATH=backend python research_notes/tn-2026-11-08/tn_pull.py <scratch dir>
"""
import collections
import json
import sys
from datetime import datetime
from pathlib import Path

from crashiq import osm
from crashiq.sources import tn_tdot as tn

out = Path(sys.argv[1])
HERE = Path(__file__).parent
BOX = json.loads((tn.REF / "county_boxes_tn.json").read_text())["counties"][tn.DAVIDSON]["box"]
share = lambda xs, f: round(sum(1 for x in xs if f(x)) / len(xs), 4) if xs else None      # noqa: E731

t24 = [c for c in tn.fetch_contract(BOX, [tn.DAVIDSON], [2024], out)["crashes"] if c["county_fips"] == tn.DAVIDSON]
got = tn.fetch_contract(BOX, [tn.DAVIDSON], [2025], out)
st = [c for c in got["crashes"] if c["source"] == "TDOSHS"]
na = [c for c in got["crashes"] if c["source"] == "Metro Nashville"]
dav = [c for c in st if c["county_fips"] == tn.DAVIDSON]
# TDOSHS 2024 in Davidson, for the agreement check (read straight from its layer)
s24 = tn.attributes(tn.LAYER, {"where": "Collision_Year = 2024 AND County = 'Davidson'"}, tn._post)
res = {"tdot_2024_davidson": {"n": len(t24), "gps_share": share(t24, lambda c: c["lat"] is not None),
                              "severity": dict(collections.Counter(c["severity"] for c in t24)),
                              "route_share": share(t24, lambda c: c["primary_road"]),
                              "freeway_share": share(t24, lambda c: c["is_freeway"]),
                              "collision_type": dict(collections.Counter(c["collision_type"] for c in t24).most_common(6))},
       "tdoshs_2024_davidson_rows": len(s24),
       "tdoshs_2024_davidson_severity": dict(collections.Counter(tn.SEVERITY.get(a["Crash_Type"]) for a in s24)),
       "tdoshs_2025": {"rows_in_box": len(st), "davidson": len(dav), "gps_share": share(st, lambda c: c["lat"] is not None),
                       "severity": dict(collections.Counter(c["severity"] for c in dav)),
                       "flags": {k: sum(c[k] for c in dav) for k in ("ped", "bike", "motorcycle", "heavy_truck")}},
       "nashville_2025_no_injury": {"n": len(na), "gps_share": share(na, lambda c: c["lat"] is not None),
                                    "street_share": share(na, lambda c: c["primary_road"]),
                                    "cross_street_share": share(na, lambda c: c["secondary_road"])}}


def when(c):
    return datetime.fromisoformat(c["date"]).toordinal() * 24 + (c["hour"] or 0)


grid = collections.defaultdict(list)
for c in dav:
    if c["lat"] is not None:
        grid[(round(c["lat"], 2), round(c["lon"], 2))].append(c)
dup = 0
for c in na:
    if c["lat"] is None:
        continue
    near = [s for dl in (-0.01, 0, 0.01) for dn in (-0.01, 0, 0.01)
            for s in grid[(round(c["lat"] + dl, 2), round(c["lon"] + dn, 2))]]
    dup += any(abs(when(s) - when(c)) <= 1 and osm.metres((s["lat"], s["lon"]), (c["lat"], c["lon"])) <= 100
               for s in near)
res["nashville_2025_no_injury"]["matching_a_state_crash_100m_1h"] = dup
res["nashville_2025_no_injury"]["overlap_share"] = round(dup / len(na), 4)
print(json.dumps(res, indent=1))
(HERE / "placement_sample.json").write_text(json.dumps(res, indent=1) + "\n")

# fixture: raw rows per severity x light (and manner for TDOT), the flags, Metro rows with and without an address
def pick(rows, keys):
    out, seen = [], collections.Counter()
    for a in rows:
        for k in keys(a):
            if seen[k] < 1:
                seen[k] += 1
                out.append(a)
    return list({id(a): a for a in out}.values())


raw = {n: json.loads(next(out.glob(f"tn_{n}_*.json")).read_text()) for n in ("tdot", "tdoshs", "nashville")}
fx_tdot = pick(raw["tdot"], lambda a: [("s", a["TYPEOFCRAS"], a["LIGHTCONDI"]), ("m", a["MANNEROFCO"]),
                                       ("r", (a["NBR_RT2"] or "")[:1]), ("h", a["FIRSTHARMF"] in ("Pedestrian", "Pedalcycle"))])
fx_st = pick(raw["tdoshs"], lambda a: [("s", a["Crash_Type"], a["Light_Condition"])] + [
    (k,) for k in ("Pedestrian", "Pedalcyclist", "Motorcycle_Involved", "LargeTruck_Involved") if a[k] != "-"])
fx_na = [a for a in raw["nashville"] if a.get("Street_Address")][:6] + [a for a in raw["nashville"]
                                                                        if not a.get("Street_Address")][:1]
fx = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "tn_crashes.json"
fx.write_text(json.dumps({"source": [tn.LAYER_TDOT, tn.LAYER, tn.NASHVILLE], "recorded": "2026-11-08", "box": BOX,
                          "tdot": fx_tdot, "state": fx_st, "nashville": fx_na}, indent=0))
print("fixture", len(fx_tdot), len(fx_st), len(fx_na), fx.stat().st_size, "bytes")
