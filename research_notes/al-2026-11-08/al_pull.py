"""Alabama: pull Jefferson County (Birmingham) 2024 and 2025 through the reader, measure it, run the California-way
placement test (hide the GPS, place street pairs on TIGER/Line 2024 Jefferson County), and record the test fixture.
    PYTHONPATH=backend python research_notes/al-2026-11-08/al_pull.py <scratch dir>
"""
import collections
import json
import math
import random
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.sources import al_care

out = Path(sys.argv[1])
HERE = Path(__file__).parent
FT250_M = 250 * 0.3048


def wilson_low(k, n, z=1.96):
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def count(where):
    q = urllib.parse.urlencode({"where": where, "returnCountOnly": "true", "f": "json"})
    req = urllib.request.Request(al_care.LAYER + "/query?" + q, headers={"User-Agent": "CrashIQ/0.1"})
    return json.load(urllib.request.urlopen(req, timeout=300))["count"]


stats_f = out / "statewide_counts.json"
if not stats_f.exists():
    per = {y: {"rows": count(al_care.year_where([y])),
               "with_point": count(f"{al_care.year_where([y])} AND Latitude > 0")} for y in range(2019, 2027)}
    stats_f.write_text(json.dumps(per))
per = json.loads(stats_f.read_text())

raw24 = al_care.fetch_raw("County='Jefferson' AND Year='2024'", out)
raw25 = al_care.fetch_raw("NumMajInj='Jefferson' AND County='2025'", out)
res = {"statewide_rows_per_year": per}
for tag, raw in (("jefferson_2024", raw24), ("jefferson_2025_shifted", raw25)):
    recs = [al_care.contract_record(a) for a in raw]
    n = len(recs)
    res[tag] = {"n": n, "shifted": sum(r["shifted_row"] for r in recs),
                "gps_share": round(sum(r["lat"] is not None for r in recs) / n, 4),
                "street_share": round(sum(bool(r["primary_road"]) for r in recs) / n, 4),
                "street_pair_share": round(sum(bool(r["primary_road"] and r["secondary_road"]) for r in recs) / n, 4),
                "severity": dict(collections.Counter(r["severity"] for r in recs)),
                "county_fips": dict(collections.Counter(r["county_fips"] for r in recs).most_common(3)),
                "collision_type": dict(collections.Counter(r["collision_type"] for r in recs).most_common(5)),
                "freeway_share": round(sum(r["is_freeway"] for r in recs) / n, 4),
                "ped": sum(r["ped"] for r in recs), "bike": sum(r["bike"] for r in recs),
                "months": dict(sorted(collections.Counter(r["date"][:7] for r in recs).items())[-3:])}

for kind in ("edges", "featnames"):
    f = out / f"tl_2024_01073_{kind}.zip"
    if not f.exists():
        urllib.request.urlretrieve(f"https://www2.census.gov/geo/tiger/TIGER2024/{kind.upper()}/{f.name}", f)
net = osm.Network(tiger.elements(out / "tl_2024_01073_edges.zip", out / "tl_2024_01073_featnames.zip"))
gate = locate.Gate(tiger_only_auto=True)     # TIGER-only network: plain Gate() auto-places nothing
recs = [al_care.contract_record(a) for a in raw24]
gps = [c for c in recs if c["lat"] is not None and c["severity"]]
nogps = [c for c in recs if c["lat"] is None and c["severity"]]
random.Random(2026).shuffle(gps)


def place(c):
    return locate.place(net, {"primary_road": c["primary_road"], "secondary_road": c["secondary_road"],
                              "offset_ft": None, "offset_dir": None})


tiers, why, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
pairs = placed = auto = hits = auto_hits = 0
sample = gps[:2000]
for c in sample:
    if not (c["primary_road"] and c["secondary_road"]):
        why["no cross street in source"] += 1
        continue
    pairs += 1
    pl = place(c)
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
        if not close and len(ex["auto >250 ft off"]) < 6:
            ex["auto >250 ft off"].append(f"{c['primary_road']} & {c['secondary_road']} "
                                          f"{osm.metres((pl.lat, pl.lon), (c['lat'], c['lon'])) / 0.3048:.0f} ft")
ng_pairs = [c for c in nogps if c["primary_road"] and c["secondary_road"]]
ng_auto = sum(gate.auto(p) for p in map(place, ng_pairs) if p.lat is not None)
k = len(sample)
res["placement"] = {"area": "Jefferson County (01073), 2024, random 2,000 with GPS (seed 2026)", "n": k,
                    "street_pair_share": round(pairs / k, 4), "tiers": dict(tiers),
                    "name_placed_share": round(placed / k, 4), "auto_share": round(auto / k, 4),
                    "gate": "Gate(tiger_only_auto=True) on a TIGER-only network",
                    "within_250ft": round(auto_hits / auto, 4) if auto else None,
                    "within_250ft_low": round(wilson_low(auto_hits, auto), 4),
                    "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
                    "not_placed": dict(why.most_common(8)), "examples": dict(ex),
                    "no_gps_crashes": len(nogps), "no_gps_with_pair": len(ng_pairs), "no_gps_auto_placed": ng_auto,
                    "no_gps_auto_share": round(ng_auto / len(nogps), 4) if nogps else None}
print(json.dumps(res, indent=1))
(HERE / "placement_sample.json").write_text(json.dumps(res, indent=1) + "\n")

# fixture: normal 2024 and shifted 2025 rows by severity x manner, plus ped, bike, motorcycle, CMV, interstate,
# no-point and Unknown-severity rows
pick, seen = [], collections.Counter()
for a in raw24 + raw25:
    c = al_care.contract_record(a)
    for key in [("sev", c["shifted_row"], c["severity"], c["collision_type"]), ("ped", c["shifted_row"], c["ped"]),
                ("bike", c["bike"]), ("mc", c["motorcycle"]), ("cmv", c["heavy_truck"]),
                ("fwy", c["shifted_row"], c["is_freeway"]), ("gps", c["shifted_row"], c["lat"] is None)]:
        if seen[key] < 1:
            seen[key] += 1
            pick.append(a)
uniq = list({a["OBJECTID"]: a for a in pick}.values())
fx = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "al_care.json"
fx.write_text(json.dumps({"source": al_care.LAYER, "recorded": "2026-11-08",
                          "features": [{"attributes": a} for a in uniq]}, indent=0))
print("fixture rows", len(uniq), fx.stat().st_size, "bytes")
