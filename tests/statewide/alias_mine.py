"""#230: draft a street alias table from the difficult bin, for the user to approve entry by entry (CLAUDE.md: nothing is
learned without user approval). Measure and draft only: the app never reads the DRAFT file.

For each city (its box + 1 km street map, as run 8), every CCRS crash 2021-2025 whose report names one road the map has
(S) and one it has under no name (R: no exact or same-core street) is a candidate. Evidence that R is map street M:
  pair votes  the crash's other road S meets exactly one map street that resembles R (similarity >= PAIR_SIM, the
              next one at least PAIR_MARGIN behind): that street is M for this crash. Different crashes (different S)
              voting for the same M is the evidence; another M with VOTE_RIVAL of the votes (or >= 2) = ambiguous
  hidden GPS  every crash with R whose police GPS fits the report (corrected #199 check) and lies within CONS_FT of
              where S meets M (self-consistent once the alias is read, the C9 rule) is placed with the alias and
              the GPS hidden; right = the chosen intersection within 250 ft of the GPS. An entry whose GPS crashes
              are right less than MIN_GPS_RIGHT of the time is excluded; the GPS never chose M, so this is held out
Impact: the difficult crashes (run 8b per-crash file, bin 2) with R in that city that the app's gate (exact +
unique_pair) places once the alias is applied.

Raw names are normalized the way the app's alias file is read (upper case, . , # ' " to spaces, single spaces).
Scope: city (CCRS city name). Crashes outside every city map aren't mined in this draft (their per-crash maps hold
only the named roads, so they can't show what R is).

Run: python tests/statewide/alias_mine.py --shard 0/3 --part a0 ; then --merge a0 a1 a2
Writes data/statewide/alias_<part>.csv; --merge writes data/reference/street_aliases_DRAFT.csv,
data/statewide/alias_excluded.csv and data/statewide/alias_review.md.
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
MIN_VOTES, MIN_AGREE, VOTE_RIVAL, TOL_M = 3, 0.8, 0.2, 250 * 0.3048
PAIR_SIM, PAIR_MARGIN, MIN_GPS_RIGHT, CONS_FT = 0.75, 0.10, 0.90, 400.0
NOT_A_STREET = re.compile(r"\b(PARKING|LOT|PRIVATE|PROPERTY|DRIVEWAY|ALLEY|NOT STATED|UNKNOWN|UNK|N/?A)\b")
COLS = ["scope_type", "scope", "county_code", "raw", "replacement", "map_street", "votes", "agreement_pct", "rival",
        "similarity", "crashes_with_name", "difficult_with_name", "would_place", "holdout_k", "holdout_n", "holdout_pct",
        "holdout_low", "examples", "kind", "status"]


def norm(raw: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[.,#'\"]", " ", (raw or "").upper())).strip()


def mine(shard: tuple[int, int], part: str, only: str | None = None) -> None:
    from crashiq import locate, names, osm

    from bin2_whatif import wilson_low

    import citywide as cw
    import corridors
    import osm_local

    with open(DATA / "coverage_crashes_r8b.csv") as f:
        cov = {r["collision_id"]: (r["outcome"], r["bin"], r["county_code"]) for r in csv.DictReader(f)}
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    cities = Counter()
    for (rid,) in con.execute("SELECT rid FROM _meta WHERE tbl = 'crashes'").fetchall():
        for (c,) in con.execute(f'SELECT "City Name" FROM "{rid}"'):
            cities[c or ""] += 1
    order = [c for c, _ in cities.most_common() if c and bounds.get(corridors.norm_city(c))]
    gate = locate.Gate()
    out = open(DATA / f"alias_{part}.csv", "w", newline="")
    w = csv.DictWriter(out, [c for c in COLS if c != "kind"] + ["excluded_because"])
    w.writeheader()
    for i, city in enumerate(order):
        if (only and city != only) or (not only and i % shard[1] != shard[0]):
            continue
        net = osm.Network(osm_local.network_in_box(local, bounds[corridors.norm_city(city)]["rel"]))
        found_cache: dict[str, list] = {}

        def found(raw):
            if raw not in found_cache:
                k = names.street_key(raw)
                found_cache[raw] = (locate._keys_matching(net, k) or locate._same_core_keys(net, k)) if k else []
            return found_cache[raw]
        seen, cand = set(), defaultdict(list)          # R -> [(crash, S raw, role)]
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in seen or cid not in cov:
                continue
            seen.add(cid)
            p, s = norm(c.get("primary_road")), norm(c.get("secondary_road"))
            for r_, o_ in ((p, s), (s, p)):
                if not r_ or not o_ or NOT_A_STREET.search(r_) or not names.street_key(r_):
                    continue
                if found(r_) or not found(o_):
                    continue
                cand[r_].append((c, o_))
        cross_cache: dict[str, dict] = {}

        def crossing(o_):
            """core -> a map street key, for every street that meets the report's other road S on this map."""
            if o_ not in cross_cache:
                sk = set(found(o_))
                cr = {}
                for k in sk:
                    for n in net.nodes_of.get(k, ()):
                        for m in net.keys_at.get(n, ()):
                            if m not in sk:
                                cr.setdefault(m.core.replace(" ", ""), m)
                cross_cache[o_] = cr
            return cross_cache[o_]
        for r_, items in cand.items():
            kr = names.street_key(r_)
            pair_votes, label, ex = Counter(), {}, []
            for c, o_ in items:
                sc = sorted(((names.similarity(kr, m), core, m) for core, m in crossing(o_).items()), key=lambda t: -t[0])
                if not sc or sc[0][0] < PAIR_SIM or (len(sc) > 1 and sc[1][0] > sc[0][0] - PAIR_MARGIN):
                    continue                    # no cross street of S resembles R, or two do: no vote
                pair_votes[sc[0][1]] += 1
                label.setdefault(sc[0][1], net.label.get(sc[0][2]) or sc[0][2].core)
                if len(ex) < 3:
                    ex.append(str(c["crash_id"]))
            n_votes = sum(pair_votes.values())
            diff = sum(1 for c, _ in items if cov[str(c["crash_id"])][1] == "2")
            if n_votes == 0:
                continue
            (top, top_n), *rest = pair_votes.most_common()
            rival = rest[0][1] if rest else 0
            sim = names.similarity(kr, names.street_key(label[top])) if names.street_key(label[top]) else 0.0
            # hidden GPS, held out (the GPS never chose M): crashes with R whose police GPS fits the report and lies
            # within CONS_FT of where S meets M (self-consistent with the report once the alias is read, as C9),
            # placed with the alias and the GPS hidden; right = the chosen intersection within 250 ft of the GPS
            al = {r_: norm(label[top])}
            mk = [m for m in net.streets if m.core.replace(" ", "") == top]
            hk = hn = 0
            for c, o_ in items:
                cid = str(c["crash_id"])
                if cov[cid][0] != "gps_usable" or c.get("lat") is None:
                    continue
                g = (c["lat"], c["lon"])
                meet = locate._shared_nodes(net, found(o_), mk)
                if not any(osm.metres(net.coord[n], g) <= CONS_FT * 0.3048 for n in meet):
                    continue
                pl = locate.place(net, {**c, "lat": None, "lon": None}, aliases=al)
                if gate.auto(pl) and pl.node is not None:
                    hn += 1
                    hk += osm.metres(net.coord[pl.node], g) <= TOL_M
            why = []
            if n_votes < MIN_VOTES:
                why.append(f"only {n_votes} crashes point to one street")
            if top_n / n_votes < MIN_AGREE:
                why.append(f"agreement {100 * top_n / n_votes:.0f}%")
            if rival >= 2 or (rival and rival / n_votes >= VOTE_RIVAL):
                why.append(f"ambiguous: {label.get(rest[0][0])} has {rival} crashes")
            if hn and wilson_low(hk, hn) is not None and hk / hn < MIN_GPS_RIGHT:
                why.append(f"hidden GPS right only {hk}/{hn}")
            would = 0
            if not why:
                for c, o_ in items:
                    if cov[str(c["crash_id"])][1] == "2" and gate.auto(locate.place(net, c, aliases=al)):
                        would += 1
            w.writerow({"scope_type": "city", "scope": city, "county_code": cov[str(items[0][0]["crash_id"])][2],
                        "raw": r_, "replacement": norm(label[top]), "map_street": label[top], "votes": n_votes,
                        "agreement_pct": round(100 * top_n / n_votes, 1), "rival": label.get(rest[0][0]) if rest else "",
                        "similarity": round(sim, 2), "crashes_with_name": len(items), "difficult_with_name": diff,
                        "would_place": would, "holdout_k": hk, "holdout_n": hn,
                        "holdout_pct": round(100 * hk / hn, 1) if hn else "", "holdout_low": wilson_low(hk, hn) if hn else "",
                        "examples": " ".join(ex), "status": "proposed" if not why else "excluded",
                        "excluded_because": "; ".join(why)})
        out.flush()
        print(f"[{i + 1}/{len(order)}] {city}: {len(cand)} unmatched names", flush=True)
    out.close()
    print("EXIT: finished", flush=True)


ABBREV = {"JR": "JUNIOR", "SR": "SENIOR", "EXPWY": "EXPRESSWAY", "EXPY": "EXPRESSWAY", "EXWY": "EXPRESSWAY",
          "EX": "EXPRESSWAY", "RT": "ROUTE", "RTE": "ROUTE", "PW": "PARKWAY", "PY": "PARKWAY", "PKWY": "PARKWAY",
          "TRL": "TRAIL", "TR": "TRAIL", "HW": "HIGHWAY", "HWY": "HIGHWAY", "BL": "BOULEVARD", "BLVD": "BOULEVARD",
          "AV": "AVENUE", "AVE": "AVENUE", "WY": "WAY", "ST": "STREET", "DR": "DRIVE", "CT": "COURT", "LN": "LANE",
          "PL": "PLACE", "CIR": "CIRCLE", "TER": "TERRACE", "RD": "ROAD", "CYN": "CANYON", "MTN": "MOUNTAIN",
          "N": "NORTH", "S": "SOUTH", "E": "EAST", "W": "WEST", "FWY": "FREEWAY", "HTS": "HEIGHTS", "VLY": "VALLEY"}


def kind(raw: str, map_street: str) -> str:
    """abbreviation: the map name is the report name with standard abbreviations spelled out (a name-cleaner rule
    would fix it everywhere); local spelling: anything else (a true per-city alias)."""
    a = [ABBREV.get(t, t) for t in norm(raw).split()]
    b = norm(map_street).split()
    return "abbreviation (cleaner rule)" if a == b else "local spelling or name"


def route_mismatch(raw: str, map_street: str) -> bool:
    """A route number in the report that the map street doesn't carry (RT 710 is not CA 1)."""
    from crashiq import names
    m = set(names.ROUTE_ANY.findall(norm(raw)))
    n = set(re.findall(r"\d+", map_street))
    return bool(m) and bool(n) and not (m & n)       # a map name without a number (Pacific Coast Highway) is no conflict


def merge(parts: list[str]) -> None:
    rows = []
    for p in parts:
        with open(DATA / f"alias_{p}.csv") as f:
            rows += list(csv.DictReader(f))
    for r in rows:
        r["kind"] = kind(r["raw"], r["map_street"])
        if r["status"] == "proposed" and route_mismatch(r["raw"], r["map_street"]):
            r["status"] = "excluded"
            r["excluded_because"] = f"route number mismatch ({r['raw']} vs {r['map_street']})"
    prop = sorted((r for r in rows if r["status"] == "proposed"), key=lambda r: -int(r["would_place"]))
    exc = [r for r in rows if r["status"] != "proposed"]
    ref = ROOT / "data" / "reference" / "street_aliases_DRAFT.csv"
    with open(ref, "w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        for r in prop:
            w.writerow({k: r[k] for k in COLS})
    with open(DATA / "alias_excluded.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS + ["excluded_because"])
        w.writeheader()
        w.writerows(exc)
    from bin2_whatif import wilson_low
    hk = sum(int(r["holdout_k"]) for r in prop)
    hn = sum(int(r["holdout_n"]) for r in prop)
    place = sum(int(r["would_place"]) for r in prop)
    print(f"{len(prop)} proposed, {len(exc)} excluded; would place {place:,} difficult crashes; held-out right "
          f"intersection {hk}/{hn}")
    nogps = sum(1 for r in prop if r["holdout_n"] == "0")
    nogps_place = sum(int(r["would_place"]) for r in prop if r["holdout_n"] == "0")
    kinds, kplace = Counter(r["kind"] for r in prop), Counter()
    for r in prop:
        kplace[r["kind"]] += int(r["would_place"])
    why = Counter()
    for r in exc:
        for x in r["excluded_because"].split("; "):
            why[re.sub(r"\d+", "N", x.split(":")[0].split(" (")[0])] += 1
    one_off = sum(1 for r in exc if r["votes"] == "1")
    route_sfx = [r for r in prop + exc if re.search(r"\s-\s*(SR|RT|US|I)\s*\d+|\((N|S|E|W)\)$", r["raw"])]
    md = ["# Street alias table: DRAFT for your review (#230)", "",
          "Measure and draft only: the app doesn't read this file. Every entry needs your yes before it is used "
          "(CLAUDE.md). Basis: CCRS mirror 2026-10-19, OSM 2026-10-18, run-8 street maps (city box + 1 km), app code "
          "main. Scope: one city each (aliases are local).", "",
          "## How an entry is proposed",
          "- A report name that matches no street on the city's map, in crashes whose other street is on the map.",
          "- Evidence it is map street M: in at least 3 crashes, the other street meets exactly one street that "
          "resembles the name (similarity >= 0.75, clearly ahead of the next), and at least 80% of those crashes point "
          "to the same M; no second street with 20% (or 2 crashes) of them.",
          "- Check on hidden police GPS: the crashes with that name whose GPS agrees with the report (once the alias is "
          "read) are placed with the alias and the GPS hidden; an entry is dropped if fewer than 90% land at the right "
          "intersection. The GPS never chose M, so this is a held-out check.", "",
          "## Summary", "",
          f"- **{len(prop)} entries proposed**, which would place **{place:,} difficult crashes** with the app's current "
          f"gate. On hidden GPS they are right at the intersection {hk:,} of {hn:,} times"
          + (f" ({100 * hk / hn:.1f}%, 95% low {wilson_low(hk, hn)}%)." if hn else "."),
          f"- By kind: {kinds.get('abbreviation (cleaner rule)', 0)} entries ({kplace.get('abbreviation (cleaner rule)', 0):,} "
          "crashes) are standard abbreviations spelled out (JR = Junior, EXPWY = Expressway, RT = Route, PW = Parkway, "
          "TRL = Trail, HW = Highway): one name-cleaner rule would fix them in every city, so they are better approved as "
          f"rules than as entries. {kinds.get('local spelling or name', 0)} entries ({kplace.get('local spelling or name', 0):,} "
          "crashes) are local spellings or names (HAWTHORN BL = Hawthorne Boulevard, FAIRMONT AV = Fairmount Avenue): the "
          "real alias table.",
          f"- {nogps} of the {len(prop)} entries ({nogps_place:,} crashes) have no crash with GPS to check them: they "
          "rest on the street evidence alone (marked \"no GPS to check\"); the rest are checked as above.",
          f"- {len(exc):,} candidates excluded: " + "; ".join(f"{k} {v:,}" for k, v in why.most_common()) + ".",
          f"- The long tail: {one_off:,} candidates rest on a single crash (one-off misspellings such as MAONOLIA, "
          "HYPE PARK DR). A table can't cover them; the fuzzy tier holds them for review today.",
          f"- {len(route_sfx)} candidates are one pattern, a route number after the name (\"PACIFIC COAST HWY - SR1\", "
          "\"BEACH BL - SR39\") or a direction in brackets (\"(N)\"): better fixed once in the name cleaner (a rule, "
          "like #212) than city by city.", "",
          "## Top entries by crashes they would place", "",
          "| # | City | Report says | Map street | Kind | Crashes pointing to it | Difficult crashes with the name | "
          "Would place | Hidden GPS right | Example crash ids |", "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(prop[:40], 1):
        g = f"{r['holdout_k']}/{r['holdout_n']}" if r["holdout_n"] != "0" else "no GPS to check"
        md.append(f"| {i} | {r['scope']} | {r['raw']} | {r['map_street']} | {r['kind'].split(' (')[0]} | "
                  f"{r['votes']} ({r['agreement_pct']}%) | "
                  f"{r['difficult_with_name']} | {r['would_place']} | {g} | {r['examples']} |")
    md += ["", f"All {len(prop)} entries: data/reference/street_aliases_DRAFT.csv (status `proposed`). Excluded "
           "candidates with their reason: data/statewide/alias_excluded.csv."]
    (DATA / "alias_review.md").write_text("\n".join(md) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--part")
    ap.add_argument("--merge", nargs="*")
    ap.add_argument("--only-city")
    a = ap.parse_args()
    if a.merge:
        merge(a.merge)
    else:
        mine(tuple(int(x) for x in a.shard.split("/")), a.part, a.only_city)
