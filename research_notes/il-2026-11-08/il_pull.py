"""Illinois: pull a Chicago sample through the reader's own calls, measure it, run the California-way placement test
(hide the GPS, place street pairs on TIGER/Line 2024 Cook and DuPage counties), and record the test fixture.
    PYTHONPATH=backend python research_notes/il-2026-11-08/il_pull.py <scratch dir>
"""
import collections
import json
import math
import random
import sys
import urllib.request
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.sources import il_idot

out = Path(sys.argv[1])
HERE = Path(__file__).parent
BOX = (41.85, -87.75, 41.95, -87.62)                     # central and west-side Chicago
DUPAGE = (41.75, -88.20, 41.95, -87.92)                  # DuPage suburbs: Naperville to Elmhurst
FT250_M = 250 * 0.3048


def wilson_low(k, n, z=1.96):
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


raw = {}
for y in (2025, 2019, 2014):
    f = out / f"chicago_{y}.json"
    if not f.exists():
        f.write_text(json.dumps(il_idot.fetch_year(BOX if y == 2025 else (41.88, -87.66, 41.89, -87.64), y)))
    raw[y] = json.loads(f.read_text())
rows = raw[2025]
recs = [il_idot.contract_record(r["attributes"], r["geometry"], 2025) for r in rows]
n = len(recs)
res = {"area": f"Chicago box {BOX}, 2025 layer, every row", "n": n,
       "gps_share": round(sum(c["lat"] is not None for c in recs) / n, 4),
       "primary_share": round(sum(bool(c["primary_road"]) for c in recs) / n, 4),
       "street_pair_share": round(sum(bool(c["primary_road"] and c["secondary_road"]) for c in recs) / n, 4),
       "house_number_share": round(sum(bool(c["house_number"]) for c in recs) / n, 4),
       "offset_share": round(sum(c["offset_ft"] is not None for c in recs) / n, 4),
       "severity": dict(collections.Counter(c["severity"] for c in recs)),
       "county": dict(collections.Counter(c["county_fips"] for c in recs).most_common(3)),
       "freeway_share": round(sum(c["is_freeway"] for c in recs) / n, 4),
       "contract_errors": 0}
from crashiq import packs  # noqa: E402
pack = packs.get("IL")
res["contract_errors"] = sum(bool(packs.check_crash(c, pack)) for c in recs if c["lat"] is not None)

def placement(recs, fips, area):
    for kind in ("edges", "featnames"):
        f = out / f"tl_2024_{fips}_{kind}.zip"
        if not f.exists():
            urllib.request.urlretrieve(f"https://www2.census.gov/geo/tiger/TIGER2024/{kind.upper()}/{f.name}", f)
    net = osm.Network(tiger.elements(out / f"tl_2024_{fips}_edges.zip", out / f"tl_2024_{fips}_featnames.zip"))
    gate = locate.Gate(tiger_only_auto=True)     # TIGER-only network: plain Gate() auto-places nothing
    cs = [c for c in recs if c["county_fips"] == fips and c["lat"] is not None]
    random.Random(2026).shuffle(cs)
    sample = cs[:2000]
    tiers, why, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    pairs = placed = auto = hits = auto_hits = 0
    for c in sample:
        if not (c["primary_road"] and c["secondary_road"]):
            why["no cross street in source"] += 1
            continue
        pairs += 1
        pl = locate.place(net, {"primary_road": c["primary_road"], "secondary_road": c["secondary_road"],
                                "offset_ft": c["offset_ft"], "offset_dir": c["offset_dir"]})
        tiers[pl.tier] += 1
        if pl.lat is None:
            why[pl.note or pl.tier] += 1
            if len(ex[pl.note]) < 6:
                ex[pl.note].append(f"{c['primary_road']} & {c['secondary_road']}")
            continue
        placed += 1
        close = osm.metres((pl.lat, pl.lon), (c["lat"], c["lon"])) <= FT250_M
        hits += close
        if gate.auto(pl):
            auto += 1
            auto_hits += close
    k = len(sample)
    return {"area": area, "n": k, "street_pair_share": round(pairs / k, 4), "tiers": dict(tiers),
            "name_placed_share": round(placed / k, 4), "auto_share": round(auto / k, 4),
            "gate": "Gate(tiger_only_auto=True) on a TIGER-only network",
            "within_250ft": round(auto_hits / auto, 4) if auto else None,
            "within_250ft_low": round(wilson_low(auto_hits, auto), 4),
            "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
            "not_placed": dict(why.most_common(8)), "examples": dict(ex)}


res["placement"] = placement(recs, "17031", "Cook County (17031) inside the Chicago box, 2025, random 2,000 with GPS "
                                            "(seed 2026)")
f = out / "dupage_2025.json"
if not f.exists():
    f.write_text(json.dumps(il_idot.fetch_year(DUPAGE, 2025)))
dp = [il_idot.contract_record(r["attributes"], r["geometry"], 2025) for r in json.loads(f.read_text())]
res["placement_dupage"] = placement(dp, "17043", f"DuPage County (17043) box {DUPAGE}, 2025, random 2,000 with GPS "
                                                 "(seed 2026)")
res["placement_dupage"]["source_rows"] = len(dp)
res["placement_dupage"]["house_number_share"] = round(sum(bool(c["house_number"]) for c in dp) / len(dp), 4)
print(json.dumps(res, indent=1))
(HERE / "placement_sample.json").write_text(json.dumps(res, indent=1) + "\n")

# fixture: 2025 rows by severity x first-crash type, ped/bike/freeway/offset/pair rows; 4 rows each of 2019 and 2014
pick, seen = [], collections.Counter()
for r, c in zip(rows, recs):
    for key in [("sev", c["severity"], c["collision_type"]), ("ped", c["ped"]), ("bike", c["bike"]),
                ("fwy", c["is_freeway"]), ("off", c["offset_ft"] is not None), ("pair", bool(c["secondary_road"])),
                ("light", c["lighting"])]:
        if seen[key] < 1:
            seen[key] += 1
            pick.append(r)
uniq = list({r["attributes"]["CrashID"]: {"year": 2025, **r} for r in pick}.values())[:40]
for y in (2019, 2014):
    by = {}
    for r in raw[y]:
        by.setdefault(r["attributes"].get("CrashSeverityCd"), r)
    uniq += [{"year": y, **r} for r in list(by.values())[:4]]
uniq[-1] = {**uniq[-1], "geometry": None}            # one row with no point
fx = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "il_idot.json"
fx.write_text(json.dumps({"source": il_idot.BASE, "recorded": "2026-11-08", "box": BOX, "rows": uniq}, indent=0))
print("fixture rows", len(uniq), fx.stat().st_size, "bytes")
