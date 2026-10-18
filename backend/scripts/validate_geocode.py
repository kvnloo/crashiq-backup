"""Hidden-truth geocoding test (issue #1, PR #16).

Population: one police agency's crash reports in CCRS: the crashes CrashIQ must place without GPS.
Truth: that agency's own geocoded location for the same report, from the city's open data, linked by report
number (SF: DataSF case_id; LA: LAPD dr_no). Correct = within 250 ft (76.2 m) of the truth point.
Rules are tuned on the dev half and reported once on the test half. Lower bounds are Wilson score, 95%.

Years: the most recent complete calendar years with final (non-preliminary) CCRS records and published agency
truth. Checked 2026-10-18: 2025 has no preliminary SFPD/LAPD rows, so it is included.

    python backend/scripts/validate_geocode.py --city sf --split test --jev
"""
import argparse, json, math, random, sys, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crashiq import locate, osm
from crashiq.jev import JevPicker
from crashiq.names import load_aliases, same_core, similarity, street_key
from crashiq.sources import ca_ccrs

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache"
TOL_M = 250 * 0.3048
CITIES = {
    # name, CCRS agency (NCIC), OSM boundary (Wikidata), years, truth source
    "sf": ("San Francisco", "3801", "Q62", (2023, 2024, 2025), "datasf"),
    "la": ("Los Angeles", "1942", "Q65", (2024, 2025), "lapd"),
}
# LAPD's open-data points sit at the intersection even when the report gives a distance (2026-10-18: median 6 m
# from the intersection vs 92 m from the offset point, n=472). There, score the chosen intersection, not the offset.
SCORE_AT_INTERSECTION = {"la"}
CODE_TIERS = ("address", "exact", "relaxed", "near", "fuzzy")


def wilson_low(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / n
    return (p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n)


def _socrata(url):
    rows, off = [], 0
    while True:
        with urllib.request.urlopen(f"{url}&$limit=50000&$offset={off}", timeout=180) as r:
            batch = json.load(r)
        rows += batch
        if len(batch) < 50000:
            return rows
        off += 50000


def truth_rows(kind, years):
    """Agency open data -> {report_number: {lat, lon, primary_rd, secondary_rd, distance}}, cached."""
    cache = CACHE / f"truth_{kind}_{'_'.join(map(str, years))}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    out = {}
    if kind == "datasf":
        yrs = ",".join(f"%27{y}%27" for y in years)
        for r in _socrata("https://data.sf.gov/resource/ubvf-ztfx.json?$select=case_id_pkey,tb_latitude,tb_longitude,"
                          f"primary_rd,secondary_rd,distance&$where=accident_year%20in({yrs})"):
            if r.get("tb_latitude") and r.get("tb_longitude"):
                out[r["case_id_pkey"]] = {"lat": float(r["tb_latitude"]), "lon": float(r["tb_longitude"]),
                                          "primary_rd": r.get("primary_rd"), "secondary_rd": r.get("secondary_rd"),
                                          "distance": r.get("distance")}
    elif kind == "lapd":
        for y in years:
            for b in _socrata("https://data.lacity.org/resource/d5tf-ez2w.json?$select=dr_no,location,cross_street,location_1"
                              f"&$where=date_occ%20between%20%27{y}-01-01T00:00:00%27%20and%20%27{y}-12-31T23:59:59%27"):
                loc = b.get("location_1") or {}
                lat, lon = float(loc.get("latitude") or 0), float(loc.get("longitude") or 0)
                if lat and lon:  # LAPD uses 0,0 for unknown
                    out[b["dr_no"]] = {"lat": lat, "lon": lon, "primary_rd": " ".join((b.get("location") or "").split()),
                                       "secondary_rd": " ".join((b.get("cross_street") or "").split()), "distance": None}
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out))
    return out


def load_linked(city, seed):
    """CCRS crashes linked to truth, with every cleaning and hygiene step counted."""
    _, ncic, _, years, kind = CITIES[city]
    where = f"\"NCIC Code\"='{ncic}'"
    crashes, log = [], Counter()
    for y in years:
        crashes += ca_ccrs.fetch(y, where, CACHE)
        for k, v in ca_ccrs.cleaning_log(y, where, CACHE).items():
            log[f"ccrs_{k}"] += v
    for c in crashes:  # LAPD writes 2401-07452 in CCRS and 240107452 in its own data
        c["report_number"] = c["report_number"].replace("-", "")
    truth = truth_rows(kind, years)
    log["truth_records"] = len(truth)
    n_ccrs = Counter(c["report_number"] for c in crashes)

    # Truth hygiene. NOTE: the "unrelated streets" filter uses truth street names to select the sample. That is
    # selection, not leakage (truth never reaches the locator), and its count is reported so its effect is visible.
    def resembles(c, t):
        a = [street_key(c["primary_road"]), street_key(c["secondary_road"])]
        b = [street_key(t.get("primary_rd")), street_key(t.get("secondary_rd"))]
        return any(x and y and similarity(x, y) >= 0.75 for x in a for y in b)

    linked = []
    for c in crashes:
        t = truth.get(c["report_number"])
        if not t:
            log["no_truth_record"] += 1
        elif not c["report_number"] or n_ccrs[c["report_number"]] > 1:
            log["dropped_duplicate_or_blank_report_number"] += 1
        elif not resembles(c, t):
            log["dropped_truth_streets_unrelated"] += 1
        else:
            dist = str(t.get("distance") or "")
            linked.append(dict(c, truth=(t["lat"], t["lon"]), truth_streets=(t.get("primary_rd"), t.get("secondary_rd")),
                               truth_offset=float(dist) if dist.replace(".", "").isdigit() else 0.0))
    log["linked"] = len(linked)
    random.Random(seed).shuffle(linked)
    return linked, dict(log)


def score(net, pl, c, city):
    if pl.lat is None:
        return None
    if city in SCORE_AT_INTERSECTION and pl.node is not None:
        return osm.metres(net.coord[pl.node], c["truth"])
    return osm.metres((pl.lat, pl.lon), c["truth"])


def int_ok(net, node, c):
    """Matcher's own job: is the chosen intersection the one the agency's record names? None if not checkable."""
    a, b = (street_key(x) for x in c.get("truth_streets", (None, None)))
    if node is None or not a or not b:
        return None
    near = [m for m in net.intersections if osm.metres(net.coord[m], net.coord[node]) <= locate.CLUSTER_M]
    keys = {k for m in near for k in net.keys_at[m]}
    return any(same_core(a, k) for k in keys) and any(same_core(b, k) for k in keys)


def arm_line(name, rows, auto):
    sel = [r for r in rows if auto(r)]
    k = sum(r["ok"] for r in sel)
    return (f"{name:44s} {len(sel):6d} {len(sel)/len(rows):8.1%} {k/max(1,len(sel)):9.1%} "
            f"{wilson_low(k, len(sel)):8.1%}"), {"auto": len(sel), "coverage": len(sel)/len(rows),
                                                 "accuracy": k/max(1, len(sel)), "wilson_low": wilson_low(k, len(sel))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", choices=list(CITIES), default="sf")
    ap.add_argument("--split", choices=["dev", "test"], required=True, help="tune on dev, report on test")
    ap.add_argument("--seed", type=int, default=20261018)
    ap.add_argument("--jev", action="store_true", help="ask Jev for a suggestion on every non-exact crash")
    ap.add_argument("--jev-model", default="jev-1.13.0")
    ap.add_argument("--no-address", action="store_true", help="skip the OSM address tier (large cities)")
    a = ap.parse_args()

    cname, ncic, wikidata, years, _ = CITIES[a.city]
    net = osm.Network(osm.fetch(wikidata, CACHE))
    addresses = None if a.no_address else locate.AddressIndex(osm.fetch_addresses(wikidata, CACHE))
    aliases = load_aliases(ROOT / "data" / "aliases" / f"{a.city}.csv")
    linked, cleaning = load_linked(a.city, a.seed)
    half = len(linked) // 2
    sample = linked[:half] if a.split == "dev" else linked[half:]
    print(f"{cname} · agency {ncic} · years {years} · {a.split} half: {len(sample)} crashes · aliases: {len(aliases)}")
    print("cleaning:", json.dumps(cleaning))

    rows = []
    for c in sample:
        pl = locate.place(net, c, addresses=addresses, aliases=aliases)
        err = score(net, pl, c, a.city)
        rows.append({"report": c["report_number"], "primary": c["primary_road"], "secondary": c["secondary_road"],
                     "offset_ft": c["offset_ft"], "dir": c["offset_dir"], "tier": pl.tier, "note": pl.note,
                     "err_m": err, "ok": err is not None and err <= TOL_M, "node": pl.node,
                     "int_ok": int_ok(net, pl.node, c),
                     "offset_lost": bool(c.get("truth_offset")) and not c.get("offset_ft")})

    spend = None
    if a.jev:
        picker = JevPicker(CACHE / f"jev_choices_{a.city}.json", max_calls=3000, model=a.jev_model)
        idx = [i for i, r in enumerate(rows) if r["tier"] not in ("exact", "address")]
        def run(i):
            c = sample[i]
            pl = locate.place_with_jev(net, c, picker, cname, aliases=aliases)
            err = score(net, pl, c, a.city)
            rows[i]["jev"] = {"tier": pl.tier, "p": pl.p, "p2": pl.p2, "err_m": err,
                              "ok": err is not None and err <= TOL_M, "int_ok": int_ok(net, pl.node, c)}
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(run, idx))
        picker.save()
        spend = picker.spend()
        print("jev spend:", json.dumps(spend))

    print(f"offset in the agency's record but missing in CCRS: {sum(r['offset_lost'] for r in rows)} of {len(rows)}")
    print("\nBy code tier         placed   accuracy  Wilson 95% low | right intersection")
    for t in CODE_TIERS:
        rs = [r for r in rows if r["tier"] == t]
        if rs:
            k = sum(r["ok"] for r in rs)
            iv = [r for r in rs if r["int_ok"] is not None]
            ik = sum(bool(r["int_ok"]) for r in iv)
            print(f"  {t:16s} {len(rs):7d} {k/len(rs):10.1%} {wilson_low(k, len(rs)):10.1%}   | "
                  + (f"{ik/len(iv):.1%} (low {wilson_low(ik, len(iv)):.1%}, n={len(iv)})" if iv else "n/a"))
    print(f"  {'review':16s} {sum(r['tier'] == 'review' for r in rows):7d}")

    # Arms: what auto-places in each pipeline. Address-tier crashes are excluded from every arm (user decision).
    J = lambda r: "jev" in r and r["jev"]["tier"] == "jev"
    jr = lambda r: dict(r, ok=r["jev"]["ok"]) if J(r) else r
    arms = {
        "A  exact only (default gate)": (rows, lambda r: r["tier"] == "exact"),
        "B  exact + relaxed + near + fuzzy": (rows, lambda r: r["tier"] in ("exact", "relaxed", "near", "fuzzy")),
    }
    if a.jev:
        arms["C  exact + Jev on all leftovers"] = ([jr(r) for r in rows], lambda r: r["tier"] == "exact" or J(r))
        cp = [r if r["tier"] in ("exact", "fuzzy") else jr(r) for r in rows]
        arms["C' exact + fuzzy + Jev on the rest"] = (cp, lambda r: r["tier"] in ("exact", "fuzzy") or (J(r) and r["tier"] != "fuzzy"))
    print(f"\n{'Arm (auto-placed)':44s} {'auto':>6s} {'coverage':>8s} {'accuracy':>9s} {'W95 low':>8s}")
    arm_stats = {}
    for name, (rs, f) in arms.items():
        line, arm_stats[name] = arm_line(name, rs, f)
        print(line)

    head2head = None
    if a.jev:  # docs/03 J1 ship rule: Jev vs fuzzy at the same review rate, on the same leftover set
        L = [r for r in rows if r["tier"] not in ("exact", "address")]
        code = [r for r in L if r["tier"] in ("relaxed", "near", "fuzzy")]
        jev = sorted([r for r in L if J(r)], key=lambda r: -(r["jev"]["p"] or 0))[:len(code)]
        kc, kj = sum(r["ok"] for r in code), sum(r["jev"]["ok"] for r in jev)
        head2head = {"leftovers": len(L), "placed_each": len(code),
                     "code_fuzzy_family": {"accuracy": kc/max(1, len(code)), "wilson_low": wilson_low(kc, len(code))},
                     "jev_top_by_p": {"placed": len(jev), "accuracy": kj/max(1, len(jev)), "wilson_low": wilson_low(kj, len(jev))}}
        print(f"\nJev vs fuzzy at equal review rate, on {len(L)} leftovers: fuzzy-family {len(code)} placed, "
              f"{head2head['code_fuzzy_family']['accuracy']:.1%} · Jev top-{len(jev)} by p, {head2head['jev_top_by_p']['accuracy']:.1%}")

    out = ROOT / "data" / "results"
    out.mkdir(parents=True, exist_ok=True)
    stem = f"geocode_{a.city}_{a.split}"
    (out / f"{stem}_rows.json").write_text(json.dumps(rows))
    (out / f"{stem}_summary.json").write_text(json.dumps(
        {"city": cname, "agency": ncic, "years": years, "split": a.split, "n": len(rows), "cleaning": cleaning,
         "arms": arm_stats, "jev_vs_fuzzy": head2head, "jev_spend": spend,
         "scored_at": "intersection" if a.city in SCORE_AT_INTERSECTION else "offset point"}, indent=1))
    print(f"\nwrote {out / (stem + '_summary.json')}")


if __name__ == "__main__":
    main()
