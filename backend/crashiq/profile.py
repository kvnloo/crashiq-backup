"""C6 profile: the deterministic crash profile as cited tables. Every number a user (or the AI analyst) sees
comes from one of these tables; nothing is computed in the frontend or by AI.

Table = {id, title, columns: [{key, label}], rows: [{key, label, values: {col: value}}], provenance: {...}}
Cell address = "<table id>/<row key>/<column key>"  (e.g. "T3/A/crashes"). C10 cites these.
Per-location tables carry the location id in the table id: "T4@osm-123".

Scope: crashes assigned to a study intersection or segment ("placed"). Unmatched crashes (no location yet)
are reported in the caveats; excluded crashes are outside the study.
"""

from __future__ import annotations

import re
from collections import Counter

from fastapi import APIRouter, Request

from . import assign as assign_mod

SEVERITY_LABELS = {"K": "Fatal (K)", "A": "Suspected serious injury (A)", "B": "Suspected minor injury (B)",
                   "C": "Possible injury (C)", "U": "Injury, level not reported", "O": "Property damage only (O)"}
INJURY = set("KABCU")
DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MODES = [("ped", "Pedestrian involved"), ("bike", "Bicyclist involved"), ("motorcycle", "Motorcycle involved"),
         ("heavy_truck", "Heavy truck involved")]
UNPLACED_LIMIT = 0.10      # Q10: report flags a data limitation above this share of unplaced crashes


def r2(x):
    return None if x is None else round(x, 2)


def pct(a, b):
    return round(100.0 * a / b, 1) if b else 0.0


_DARK = re.compile(r"\bDARK\b")


def is_dark(c) -> bool:
    """Any 'Dark …' lighting (street lights on, off, or not functioning). Dusk/dawn is not dark."""
    return bool(_DARK.search((c.get("lighting") or "").upper()))


def is_unlit(c) -> bool:
    """Dark with no street lights or street lights not functioning (#34 item 14: split from lit darkness)."""
    t = (c.get("lighting") or "").upper()
    return is_dark(c) and ("NO STREET" in t or "NOT FUNCTION" in t)


def _table(tid, title, columns, rows, crashes):
    prov = Counter(c.get("location_provenance", "gps") for c in crashes)
    return {"id": tid, "title": title, "columns": [{"key": k, "label": lbl} for k, lbl in columns],
            "rows": rows, "provenance": dict(sorted(prov.items()))}


def _row(key, label, **values):
    return {"key": str(key), "label": label, "values": values}


def _dist(tid, title, crashes, field, label_of=lambda v: v or "Not stated", order=None):
    n = len(crashes)
    cnt = Counter((c.get(field) or "") for c in crashes)
    inj = Counter((c.get(field) or "") for c in crashes if c["severity"] in INJURY)
    ksi = Counter((c.get(field) or "") for c in crashes if c["severity"] in "KA")
    keys = order or sorted(cnt, key=lambda k: (-cnt[k], k))
    rows = [_row(k or "not_stated", label_of(k), crashes=cnt[k], injury_crashes=inj[k], ksi_crashes=ksi[k],
                 share_pct=pct(cnt[k], n)) for k in keys if cnt[k] or order]
    return _table(tid, title, [("crashes", "Crashes"), ("injury_crashes", "Injury crashes"),
                               ("ksi_crashes", "KSI crashes"), ("share_pct", "Share %")], rows, crashes)


def tables_for(crashes: list[dict], years: int, suffix: str = "") -> list[dict]:
    """Distribution tables T3–T11 for a set of crashes (the whole study, or one location)."""
    s = suffix
    n = len(crashes)
    sev = Counter(c["severity"] for c in crashes)
    out = [_table(f"T3{s}", "Severity (each crash counted once, at its most severe outcome)",
                  [("crashes", "Crashes"), ("share_pct", "Share %")],
                  [_row(k, SEVERITY_LABELS[k], crashes=sev[k], share_pct=pct(sev[k], n)) for k in "KABCUO"], crashes)]
    out.append(_dist(f"T4{s}", "Collision type", crashes, "collision_type", lambda v: (v or "Not stated").title()))
    out.append(_dist(f"T5{s}", "Primary collision factor", crashes, "pcf",
                     lambda v: v or "Not stated"))
    out.append(_dist(f"T6{s}", "Lighting", crashes, "lighting", lambda v: (v or "Not stated").title()))
    out.append(_dist(f"T7{s}", "Weather", crashes, "weather", lambda v: (v or "Not stated").title()))
    out.append(_dist(f"T8{s}", "Road surface", crashes, "surface", lambda v: (v or "Not stated").title()))
    hd = Counter((c.get("day_of_week"), c.get("hour")) for c in crashes)
    out.append(_table(f"T9{s}", "Crashes by hour and day of week",
                      [(str(h), f"{h:02d}") for h in range(24)] + [("unknown_hour", "Hour not stated")],
                      [_row(d, d, **{str(h): hd[(d, h)] for h in range(24)},
                            unknown_hour=sum(v for (dd, h), v in hd.items() if dd == d and h is None)) for d in DOW],
                      crashes))
    rows = []
    for key, label in MODES:
        sub = [c for c in crashes if c.get(key)]
        rows.append(_row(key, label, crashes=len(sub), ksi_crashes=sum(c["severity"] in "KA" for c in sub),
                         share_pct=pct(len(sub), n)))
    out.append(_table(f"T10{s}", "Road users involved", [("crashes", "Crashes"), ("ksi_crashes", "KSI crashes"),
                                                         ("share_pct", "Share %")], rows, crashes))
    yr = Counter(c.get("year") for c in crashes)
    out.append(_table(f"T11{s}", "Crashes by year", [("crashes", "Crashes"), ("ksi_crashes", "KSI crashes")],
                      [_row(y, str(y), crashes=yr[y], ksi_crashes=sum(1 for c in crashes if c.get("year") == y
                                                                      and c["severity"] in "KA"))
                       for y in sorted(k for k in yr if k is not None)], crashes))
    return out


def _counts(crashes):
    sev = Counter(c["severity"] for c in crashes)
    return {"crashes": len(crashes), "ksi_crashes": sev["K"] + sev["A"], "fatal_crashes": sev["K"],
            "injury_crashes": sum(sev[k] for k in INJURY), "pdo_crashes": sev["O"],
            "killed": sum(c.get("killed", 0) for c in crashes), "injured": sum(c.get("injured", 0) for c in crashes),
            "dark_crashes": sum(is_dark(c) for c in crashes), "ped_crashes": sum(bool(c.get("ped")) for c in crashes),
            "bike_crashes": sum(bool(c.get("bike")) for c in crashes)}


def segment_rate(crashes: int, years: float, aadt: float | None, length_mi: float) -> float | None:
    """Crashes per 100 million vehicle-miles (FHWA): N × 10^8 / (365 × years × AADT × length)."""
    if not aadt or not length_mi or not years:
        return None
    return crashes * 1e8 / (365 * years * aadt * length_mi)


def entering_volume(major_aadt: float | None, minor_aadt: float | None, legs: int | None) -> float | None:
    """Total entering vehicles per day from two-way AADTs (#34 item 11): a through cross street brings its whole
    two-way AADT into the intersection (major + minor); a T has one minor leg, so half of it (major + minor/2)."""
    if not major_aadt or minor_aadt is None:
        return None
    return major_aadt + (minor_aadt / 2 if legs == 3 else minor_aadt)


def intersection_rate(crashes: int, years: float, major_aadt: float | None, minor_aadt: float | None,
                      legs: int | None = None) -> float | None:
    """Crashes per million entering vehicles (HSM Ch. 4 Eq. 4-2, 4-3): N × 10^6 / (365 × years × TEV)."""
    tev = entering_volume(major_aadt, minor_aadt, legs)
    if not tev or not years:
        return None
    return crashes * 1e6 / (365 * years * tev)


def build(study: dict, net: dict, pull: dict, assignment: dict, exclude: set[str] | None = None) -> dict:
    exclude = exclude or set()
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    placed, unmatched, excluded_n = [], [], 0
    for a in assignment["assignments"]:
        c = {**by_id[a["crash_id"]], **{k: a[k] for k in ("kind", "location_id", "location_provenance")}}
        prov = c["location_provenance"] or ""
        if any(prov.startswith(e) for e in exclude):
            continue
        if a["kind"] in ("intersection", "segment"):
            placed.append(c)
        elif a["kind"] == "unmatched":
            unmatched.append(c)
        else:
            excluded_n += 1
    years_missing = pull["cleaning"].get("years_missing", [])
    years = len(pull["years"]) - len(years_missing)
    length_mi = net["length_mi"]

    # T1 summary
    tot = _counts(placed)
    summary_rows = [
        _row("crashes", "Crashes", value=tot["crashes"]),
        _row("crashes_per_year", "Crashes per year", value=r2(tot["crashes"] / years) if years else None),
        _row("ksi_crashes", "KSI crashes (fatal + suspected serious injury)", value=tot["ksi_crashes"]),
        _row("fatal_crashes", "Fatal crashes", value=tot["fatal_crashes"]),
        _row("injury_crashes", "Injury crashes (any level)", value=tot["injury_crashes"]),
        _row("pdo_crashes", "Property-damage-only crashes", value=tot["pdo_crashes"]),
        _row("killed", "People killed", value=tot["killed"]),
        _row("injured", "People injured", value=tot["injured"]),
        _row("dark_crashes", "Crashes in darkness", value=tot["dark_crashes"]),
        _row("years", "Years of data", value=years),
        _row("length_mi", "Corridor length (mi)", value=round(length_mi, 2)),
        _row("crashes_per_mi_yr", "Crashes per mile per year (all study crashes)",
             value=r2(tot["crashes"] / length_mi / years) if years and length_mi else None),
        _row("unplaced", "Crashes not yet placed (no coordinates)", value=len(unmatched)),
        _row("excluded", "Crashes outside the study area", value=excluded_n),
    ]
    tables = [_table("T1", "Study summary", [("value", "Value")], summary_rows, placed)]

    # T2 locations, corridor order (intersections and segments interleaved by station)
    names = {i["id"]: i for i in net["intersections"]}
    seg_by = {s["id"]: s for s in net["segments"]}
    groups: dict[str, list] = {}
    for c in placed:
        groups.setdefault(c["location_id"], []).append(c)
    order = []
    for i in net["intersections"]:
        if i["is_study"]:
            order.append(("intersection", i["id"], i["station_ft"]))
    for s in net["segments"]:
        order.append(("segment", s["id"], (s["from_station_ft"] + s["to_station_ft"]) / 2))
    order.sort(key=lambda t: t[2])
    rates_any = False
    loc_rows = []
    for kind, lid, _ in order:
        cs = groups.get(lid, [])
        k = _counts(cs)
        vals = {"kind": kind, **{x: k[x] for x in ("crashes", "ksi_crashes", "fatal_crashes", "injury_crashes",
                                                   "dark_crashes", "ped_crashes", "bike_crashes")},
                "crashes_per_year": r2(k["crashes"] / years) if years else None}
        if kind == "segment":
            s = seg_by[lid]
            rate = segment_rate(k["crashes"], years, s.get("aadt"), s["length_mi"])
            vals.update(length_mi=round(s["length_mi"], 3),
                        crashes_per_mi_yr=r2(k["crashes"] / s["length_mi"] / years) if years and s["length_mi"] else None,
                        aadt=s.get("aadt"), rate=r2(rate), rate_unit="per 100M VMT" if rate is not None else None)
            label = s["name"]
        else:
            it = names[lid]
            rate = intersection_rate(k["crashes"], years, it.get("major_aadt"), it.get("minor_aadt"), it.get("legs"))
            vals.update(length_mi=None, crashes_per_mi_yr=None, control=it["control"], rate=r2(rate),
                        rate_unit="per MEV" if rate is not None else None)
            label = it["name"]
        rates_any |= rate is not None
        loc_rows.append(_row(lid, label, **vals))
    tables.append(_table("T2", "Locations (corridor order)", [
        ("crashes", "Crashes"), ("crashes_per_year", "Per year"), ("ksi_crashes", "KSI"), ("fatal_crashes", "Fatal"),
        ("injury_crashes", "Injury"), ("dark_crashes", "Dark"), ("ped_crashes", "Ped"), ("bike_crashes", "Bike"),
        ("length_mi", "Length (mi)"), ("crashes_per_mi_yr", "Per mile per year"), ("rate", "Rate")], loc_rows, placed))
    tables += tables_for(placed, years)
    from . import signals as signals_mod          # C7; imported here because signals imports this module
    scr = signals_mod.screen(placed, [(r["key"], r["label"]) for r in loc_rows])
    tables.append(scr["table"])

    # Caveats (computed; shown only when they apply)
    caveats = []
    prelim = sum(c.get("preliminary", False) for c in placed)
    if prelim:
        caveats.append({"key": "preliminary", "count": prelim,
                        "text": f"{prelim} crash report{'s are' if prelim != 1 else ' is'} still preliminary (CHP may revise them)."})
    if study.get("covid_years_in_window"):
        caveats.append({"key": "covid", "text": "The window includes 2020 or 2021, when COVID-19 changed travel and crash "
                                                "patterns; compare those years with care."})
    total_known = len(placed) + len(unmatched)
    share = len(unmatched) / total_known if total_known else 0.0
    if unmatched:
        caveats.append({"key": "unplaced", "count": len(unmatched), "share_pct": pct(len(unmatched), total_known),
                        "limitation": share > UNPLACED_LIMIT,
                        "ksi": sum(c["severity"] in ("K", "A") for c in unmatched),
                        "text": (f"{len(unmatched)} crash{'es' if len(unmatched) != 1 else ''} on this corridor "
                                 f"({pct(len(unmatched), total_known)}%) have no coordinates and aren't placed yet"
                                 + (f", including {sum(c['severity'] in ('K', 'A') for c in unmatched)} fatal or "
                                    "serious-injury crash(es) not in the KSI count"
                                    if any(c["severity"] in ("K", "A") for c in unmatched) else "")
                                 + (". This is a data limitation for this study." if share > UNPLACED_LIMIT else "."))})
    u = sum(c["severity"] == "U" for c in placed)
    if u:
        caveats.append({"key": "injury_level_unknown", "count": u,
                        "text": f"{u} injury crash{'es have' if u != 1 else ' has'} no reported injury level, so KSI may be undercounted."})
    if years_missing:
        caveats.append({"key": "years_missing", "years": years_missing,
                        "text": f"CCRS has no queryable data for {', '.join(map(str, years_missing))}; those years are not in the profile."})
    if not rates_any:
        caveats.append({"key": "rates_not_computed", "text": "Crash rates were not computed (no AADT entered)."})
    if exclude:
        caveats.append({"key": "excluded_provenance", "text": f"Crashes placed by {', '.join(sorted(exclude))} are left out of this run."})

    prov = Counter(c["location_provenance"] for c in placed)
    prov["unmatched"] = len(unmatched)
    return {"study_id": study["id"], "window": {"from_year": study["from_year"], "to_year": study["to_year"],
                                                 "years_with_data": years},
            "kpis": {"crashes": "T1/crashes/value", "ksi_crashes": "T1/ksi_crashes/value",
                     "injury_crashes": "T1/injury_crashes/value", "crashes_per_mi_yr": "T1/crashes_per_mi_yr/value"},
            "tables": tables, "signals": scr["signals"], "screen_tests": scr["tests_run"], "caveats": caveats, "location_provenance": dict(sorted(prov.items())),
            "source": pull["source"], "pulled_at": pull["pulled_at"], "excluded_provenance": sorted(exclude)}


def location_profile(profile_crashes: list[dict], lid: str, years: int) -> list[dict]:
    return tables_for([c for c in profile_crashes if c["location_id"] == lid], years, suffix=f"@{lid}")


def cell(tables: list[dict], address: str):
    """Value at '<table>/<row>/<column>'; KeyError if the address doesn't exist."""
    tid, row, col = address.split("/", 2)
    t = next(t for t in tables if t["id"] == tid)
    r = next(r for r in t["rows"] if r["key"] == row)
    return r["values"][col]


router = APIRouter()


@router.get("/studies/{sid}/profile")
def get_profile(sid: str, request: Request, exclude: str = "") -> dict:
    study, net, pull, a = assign_mod.for_study(request.app.state.db, sid)
    return build(study, net, pull, a, {e for e in exclude.split(",") if e})


@router.get("/studies/{sid}/profile/locations/{lid}")
def get_location_profile(sid: str, lid: str, request: Request) -> dict:
    study, net, pull, a = assign_mod.for_study(request.app.state.db, sid)
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    placed = [{**by_id[x["crash_id"]], "location_id": x["location_id"], "location_provenance": x["location_provenance"]}
              for x in a["assignments"] if x["location_id"] == lid]
    years = len(pull["years"]) - len(pull["cleaning"].get("years_missing", []))
    return {"location_id": lid, "tables": tables_for(placed, years, suffix=f"@{lid}"),
            "crashes": [{k: c.get(k) for k in ("crash_id", "date", "hour", "day_of_week", "collision_type", "severity",
                                               "lighting", "pcf", "primary_road", "secondary_road", "lat", "lon",
                                               "location_provenance")} for c in placed]}
