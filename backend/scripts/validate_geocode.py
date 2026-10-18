"""Hidden-truth geocoding test (issue #1).

Population: SFPD crash reports in CCRS (agency 3801) — the crashes CrashIQ must place without GPS.
Truth: SFPD's own geocoded location for the same report, from DataSF (CCRS Report Number == case_id_pkey).
Correct = placed within 250 ft of the truth point.
"""
import argparse, json, math, random, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collections import Counter as _C
from concurrent.futures import ThreadPoolExecutor
from crashiq import locate, osm
from crashiq.jev import JevPicker
from crashiq.names import similarity, street_key
from crashiq.sources import ca_ccrs

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache"
SF_WIKIDATA = "Q62"
CITIES = {
    # name, CCRS agency (NCIC), OSM boundary (Wikidata), years, truth loader key
    "sf": ("San Francisco", "3801", "Q62", (2023, 2024), "datasf"),
    "la": ("Los Angeles", "1942", "Q65", (2024,), "lapd"),
}
# LAPD's open-data points sit at the intersection even when the report gives a distance (2026-10-18: median 6 m
# from the intersection vs 92 m from the offset point, n=472). There, score the chosen intersection, not the offset.
SCORE_AT_INTERSECTION = {"la"}


def truth_rows(kind, years):
    """Agency open data -> {report_number: {lat, lon, primary_rd, secondary_rd, distance}}."""
    import urllib.request
    cache = CACHE / f"truth_{kind}_{'_'.join(map(str, years))}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    out = {}
    if kind == "datasf":
        for r in json.loads((CACHE / "datasf_2023_2024.json").read_text()):
            if r.get("tb_latitude"):
                out[r["case_id_pkey"]] = {"lat": float(r["tb_latitude"]), "lon": float(r["tb_longitude"]),
                                          "primary_rd": r.get("primary_rd"), "secondary_rd": r.get("secondary_rd"),
                                          "distance": r.get("distance")}
    elif kind == "lapd":
        for y in years:
            off = 0
            while True:
                url = ("https://data.lacity.org/resource/d5tf-ez2w.json?$select=dr_no,location,cross_street,location_1"
                       f"&$where=date_occ%20between%20%27{y}-01-01T00:00:00%27%20and%20%27{y}-12-31T23:59:59%27"
                       f"&$limit=50000&$offset={off}")
                with urllib.request.urlopen(url, timeout=180) as r:
                    batch = json.load(r)
                for b in batch:
                    loc = b.get("location_1") or {}
                    lat, lon = float(loc.get("latitude") or 0), float(loc.get("longitude") or 0)
                    if lat and lon:  # LAPD uses 0,0 for unknown
                        out[b["dr_no"]] = {"lat": lat, "lon": lon, "primary_rd": " ".join((b.get("location") or "").split()),
                                           "secondary_rd": " ".join((b.get("cross_street") or "").split()), "distance": None}
                if len(batch) < 50000:
                    break
                off += 50000
    cache.write_text(json.dumps(out))
    return out
TOL_M = 250 * 0.3048


def wilson_low(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / n
    return (p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n)


def score(net, p, c, city):
    if p.lat is None:
        return None
    if city in SCORE_AT_INTERSECTION and p.node is not None:
        return osm.metres(net.coord[p.node], c["truth"])
    return osm.metres((p.lat, p.lon), c["truth"])


def int_ok(net, node, c):
    """Matcher's own job: is the chosen intersection the one SFPD's record names? None if not checkable."""
    a, b = (street_key(x) for x in c.get("truth_streets", (None, None)))
    if node is None or not a or not b:
        return None
    from crashiq.names import same_core
    near = [m for m in net.intersections if osm.metres(net.coord[m], net.coord[node]) <= locate.CLUSTER_M]
    keys = {k for m in near for k in net.keys_at[m]}
    return any(same_core(a, k) for k in keys) and any(same_core(b, k) for k in keys)


def load_sample(n, seed, city="sf"):
    _, ncic, _, years, kind = CITIES[city]
    crashes = []
    for y in years:
        crashes += ca_ccrs.fetch(y, f"\"NCIC Code\"='{ncic}'", CACHE)
    for c in crashes:  # LAPD writes 2401-07452 in CCRS and 240107452 in its own data
        c["report_number"] = c["report_number"].replace("-", "")
    truth = truth_rows(kind, years)
    # Truth hygiene (lessons 2026-10-18): CCRS has blank and duplicate report numbers, and DataSF parks
    # some records at a default point with unrelated street names. Link only unique ids, and keep a
    # truth record only if at least one of its streets resembles the CCRS streets (typos still pass).
    n_ccrs = _C(c["report_number"] for c in crashes)
    def resembles(c, t):
        a = [street_key(c["primary_road"]), street_key(c["secondary_road"])]
        b = [street_key(t.get("primary_rd")), street_key(t.get("secondary_rd"))]
        return any(x and y and similarity(x, y) >= 0.75 for x in a for y in b)
    linked, dropped = [], _C()
    for c in crashes:
        t = truth.get(c["report_number"])
        if not t:
            continue
        if not c["report_number"] or n_ccrs[c["report_number"]] > 1:
            dropped["duplicate or blank report number"] += 1
        elif not resembles(c, t):
            dropped["truth streets unrelated to CCRS streets"] += 1
        else:
            linked.append(dict(c, truth=(t["lat"], t["lon"]),
                               truth_streets=(t.get("primary_rd"), t.get("secondary_rd")),
                               truth_offset=float(t["distance"]) if str(t.get("distance") or "").replace(".", "").isdigit() else 0.0))
    print("truth records dropped:", dict(dropped))
    random.Random(seed).shuffle(linked)
    return crashes, linked, linked[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261018)
    ap.add_argument("--out", default=str(ROOT / "data" / "results"))
    ap.add_argument("--city", choices=list(CITIES), default="sf")
    ap.add_argument("--no-address", action="store_true", help="skip the OSM address tier")
    ap.add_argument("--jev", action="store_true", help="send leftovers (review + weak tiers) to Jev")
    ap.add_argument("--weak", default="near", help="comma list of code tiers that go to Jev instead of auto-placing")
    ap.add_argument("--split", choices=["dev", "test"], help="half of ALL linked crashes: tune on dev, report on test")
    a = ap.parse_args()
    cname, ncic, wikidata, years, kind = CITIES[a.city]
    net = osm.Network(osm.fetch(wikidata, CACHE))
    addresses = None if a.no_address else locate.AddressIndex(osm.fetch_addresses(wikidata, CACHE))
    allc, linked, sample = load_sample(a.n, a.seed, a.city)
    print(f"{cname} agency {ncic} crashes in CCRS {years}: {len(allc)} · linked to agency truth: {len(linked)} · sample: {len(sample)}")
    if a.split:
        half = len(linked) // 2
        sample = linked[:half] if a.split == "dev" else linked[half:]
        print(f"split: {a.split} ({len(sample)} crashes)")
    rows = []
    for c in sample:
        p = locate.place(net, c, addresses=addresses)
        err = score(net, p, c, a.city)
        rows.append({"report": c["report_number"], "primary": c["primary_road"], "secondary": c["secondary_road"],
                     "offset_ft": c["offset_ft"], "dir": c["offset_dir"], "tier": p.tier, "note": p.note,
                     "err_m": err, "ok": err is not None and err <= TOL_M, "node": p.node,
                     "int_ok": int_ok(net, p.node, c), "offset_lost": bool(c.get("truth_offset")) and not c.get("offset_ft")})
    if a.jev:
        picker = JevPicker(CACHE / f"jev_choices_{a.city}.json", max_calls=3000)
        weak = set(a.weak.split(","))
        idx = [i for i, r in enumerate(rows) if r["tier"] == "review" or r["tier"] in weak]
        def run(i):
            c = sample[i]
            p = locate.place_with_jev(net, c, picker, cname)
            err = score(net, p, c, a.city)
            rows[i].update(tier=p.tier, note=p.note, p=p.p, err_m=err, ok=err is not None and err <= TOL_M,
                           node=p.node, int_ok=int_ok(net, p.node, c))
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(run, idx))
        picker.save()
        print(f"Jev: {len(idx)} leftovers · {picker.calls} calls · {picker.input_tokens} in / {picker.output_tokens} out tokens "
              f"· ~${picker.input_tokens * 0.042 / 1e6:.4f} input cost")
        js = [r for r in rows if r["tier"] == "jev"]
        print("Jev accuracy by probability cut-off:")
        for tau in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99):
            sel = [r for r in js if (r.get("p") or 0) >= tau]
            k = sum(r["ok"] for r in sel)
            if sel:
                print(f"  p >= {tau:4}: {len(sel):4d} placed · {k/len(sel):6.1%} correct · 95% low {wilson_low(k, len(sel)):6.1%}")
    tiers = Counter(r["tier"] for r in rows)
    lost = [r for r in rows if r.get("offset_lost")]
    print(f"offset in SF's record but missing in CCRS: {len(lost)} of {len(rows)} crashes")
    print("\nTier        placed   correct   accuracy   95% low   | right intersection (checkable)")
    for t in ("address", "exact", "relaxed", "near", "fuzzy", "jev"):
        rs = [r for r in rows if r["tier"] == t]
        k = sum(r["ok"] for r in rs)
        if rs:
            iv = [r for r in rs if r.get("int_ok") is not None]
            ik = sum(bool(r["int_ok"]) for r in iv)
            itxt = f"{ik}/{len(iv)} = {ik/len(iv):.1%} (low {wilson_low(ik, len(iv)):.1%})" if iv else "n/a"
            print(f"{t:10s} {len(rs):7d} {k:9d} {k/len(rs):10.1%} {wilson_low(k, len(rs)):9.1%}   | {itxt}")
    placed = [r for r in rows if r["tier"] != "review"]
    k = sum(r["ok"] for r in placed)
    print(f"{'ALL AUTO':10s} {len(placed):7d} {k:9d} {k/max(1,len(placed)):10.1%} {wilson_low(k, len(placed)):9.1%}")
    print(f"coverage (auto-placed): {len(placed)/len(rows):.1%} · to review: {tiers['review']}")
    print("review reasons:", Counter(r["note"] for r in rows if r["tier"] == "review").most_common(5))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / f"geocode_{a.city}_rows{'_' + a.split if a.split else ''}.json").write_text(json.dumps(rows, indent=0))


if __name__ == "__main__":
    main()
