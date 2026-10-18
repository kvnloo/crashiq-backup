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
TOL_M = 250 * 0.3048


def wilson_low(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / n
    return (p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n)


def int_ok(net, node, c):
    """Matcher's own job: is the chosen intersection the one SFPD's record names? None if not checkable."""
    a, b = (street_key(x) for x in c.get("truth_streets", (None, None)))
    if node is None or not a or not b:
        return None
    from crashiq.names import same_core
    near = [m for m in net.intersections if osm.metres(net.coord[m], net.coord[node]) <= locate.CLUSTER_M]
    keys = {k for m in near for k in net.keys_at[m]}
    return any(same_core(a, k) for k in keys) and any(same_core(b, k) for k in keys)


def load_sample(n, seed):
    crashes = []
    for y in (2023, 2024):
        crashes += ca_ccrs.fetch(y, "\"NCIC Code\"='3801'", CACHE)
    truth = {r["case_id_pkey"]: r for r in json.loads((CACHE / "datasf_2023_2024.json").read_text())
             if r.get("tb_latitude") and r.get("tb_longitude")}
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
            linked.append(dict(c, truth=(float(t["tb_latitude"]), float(t["tb_longitude"])),
                               truth_streets=(t.get("primary_rd"), t.get("secondary_rd")),
                               truth_offset=float(t["distance"]) if (t.get("distance") or "0").replace(".", "").isdigit() else 0.0))
    print("truth records dropped:", dict(dropped))
    random.Random(seed).shuffle(linked)
    return crashes, linked, linked[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261018)
    ap.add_argument("--out", default=str(ROOT / "data" / "results"))
    ap.add_argument("--jev", action="store_true", help="send leftovers (review + weak tiers) to Jev")
    ap.add_argument("--weak", default="near", help="comma list of code tiers that go to Jev instead of auto-placing")
    ap.add_argument("--split", choices=["dev", "test"], help="half of ALL linked crashes: tune on dev, report on test")
    a = ap.parse_args()
    net = osm.Network(osm.fetch(SF_WIKIDATA, CACHE))
    addresses = locate.AddressIndex(osm.fetch_addresses(SF_WIKIDATA, CACHE))
    allc, linked, sample = load_sample(a.n, a.seed)
    print(f"SFPD crashes in CCRS 2023-24: {len(allc)} · linked to DataSF truth: {len(linked)} · sample: {len(sample)}")
    if a.split:
        half = len(linked) // 2
        sample = linked[:half] if a.split == "dev" else linked[half:]
        print(f"split: {a.split} ({len(sample)} crashes)")
    rows = []
    for c in sample:
        p = locate.place(net, c, addresses=addresses)
        err = osm.metres((p.lat, p.lon), c["truth"]) if p.lat is not None else None
        rows.append({"report": c["report_number"], "primary": c["primary_road"], "secondary": c["secondary_road"],
                     "offset_ft": c["offset_ft"], "dir": c["offset_dir"], "tier": p.tier, "note": p.note,
                     "err_m": err, "ok": err is not None and err <= TOL_M, "node": p.node,
                     "int_ok": int_ok(net, p.node, c), "offset_lost": bool(c.get("truth_offset")) and not c.get("offset_ft")})
    if a.jev:
        picker = JevPicker(CACHE / "jev_choices_sf.json", max_calls=3000)
        weak = set(a.weak.split(","))
        idx = [i for i, r in enumerate(rows) if r["tier"] == "review" or r["tier"] in weak]
        def run(i):
            c = sample[i]
            p = locate.place_with_jev(net, c, picker, "San Francisco")
            err = osm.metres((p.lat, p.lon), c["truth"]) if p.lat is not None else None
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
    (out / f"geocode_sf_rows{'_' + a.split if a.split else ''}.json").write_text(json.dumps(rows, indent=0))


if __name__ == "__main__":
    main()
