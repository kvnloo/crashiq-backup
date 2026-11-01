"""C6 profile: the deterministic crash profile as cited tables. Every number a user (or the AI analyst) sees
comes from one of these tables; nothing is computed in the frontend or by AI.

Table = {id, title, columns: [{key, label}], rows: [{key, label, values: {col: value}}], provenance: {...}}
Cell address = "<table id>/<row key>/<column key>"  (e.g. "T3/A/crashes"). C10 cites these.
Per-location tables carry the location id in the table id: "T4@osm-123".

Scope: crashes assigned to a study intersection or segment ("placed"). Unmatched crashes (no location yet)
are reported in the caveats; excluded crashes are outside the study.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from fastapi import APIRouter, Request

from . import pcf, assign as assign_mod
from . import study as study_mod
from . import crash_cost
from .geo import Polyline

SEVERITY_LABELS = {"K": "Fatal (K)", "A": "Suspected serious injury (A)", "B": "Suspected minor injury (B)",
                   "C": "Possible injury (C)", "U": "Injury, level not reported", "O": "Property damage only (O)"}
INJURY = set("KABCU")
DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MODES = [("ped", "Pedestrian involved"), ("bike", "Bicyclist involved"), ("ebike", "E-bike involved"),
         ("escooter", "E-scooter involved"), ("motorcycle", "Motorcycle involved"),
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


# small numbers (user decision 2026-10-25, docs/03): a share on fewer crashes than this shows as a count only on screen;
# tables and the export keep every value and mark those rows (#271)
MIN_SHARE_N = 10
SMALL_MARK = "n < 10"


def _table(tid, title, columns, rows, crashes):
    prov = Counter(c.get("location_provenance", "gps") for c in crashes)
    on_tiger = sum(1 for c in crashes if c.get("placed_on") == "tiger")
    if on_tiger:                          # visible wherever the sources are listed (#229)
        prov["of these, with a TIGER/Line-only street name or road"] = on_tiger
    by_alias = sum(1 for c in crashes if c.get("aliases_used"))
    if by_alias:                          # #235
        prov["of these, with a street name read through an approved alias"] = by_alias
    if any(k.endswith("_pct") for k, _ in columns) and not tid.startswith("T12") and len(crashes) < MIN_SHARE_N:
        for r in rows:                     # every share in this table is of the same few crashes
            r["values"]["small_base"] = SMALL_MARK
    if any("small_base" in r["values"] for r in rows) and "small_base" not in [k for k, _ in columns]:
        columns = [*columns, ("small_base", "Base")]
    return {"id": tid, "title": title, "columns": [{"key": k, "label": lbl} for k, lbl in columns],
            "rows": rows, "provenance": dict(sorted(prov.items()))}


def _row(key, label, **values):
    return {"key": str(key), "label": label, "values": values}


def _dist(tid, title, crashes, field, label_of=lambda v: v or "Not stated", order=None):
    n = len(crashes)
    cnt = Counter((c.get(field) or "") for c in crashes)
    inj = Counter((c.get(field) or "") for c in crashes if c["severity"] in INJURY)
    ksi = Counter((c.get(field) or "") for c in crashes if c["severity"] in "KA")
    lvl = {L: Counter((c.get(field) or "") for c in crashes if c["severity"] == L) for L in "KABCUO"}
    keys = order or sorted(cnt, key=lambda k: (-cnt[k], k))
    # sev_k ... sev_o per row: the bars stack the one severity ramp, so orange always means serious (#119)
    rows = [_row(k or "not_stated", label_of(k), crashes=cnt[k], injury_crashes=inj[k], ksi_crashes=ksi[k],
                 share_pct=pct(cnt[k], n), **{f"sev_{L.lower()}": lvl[L][k] for L in "KABCUO"})
            for k in keys if cnt[k] or order]
    return _table(tid, title, [("crashes", "Crashes"), ("injury_crashes", "Injury crashes"),
                               ("ksi_crashes", "KSI crashes"), ("share_pct", "Share %")], rows, crashes)


def _pcf_categories(tid: str, crashes: list[dict]) -> dict:
    """T5 grouped into the 24 SWITRS categories via CHP's own section table (#52, 1A). Crashes the table can't
    categorize keep their own rows after the categories (blank, words, CHP 00, split by year, not in the table)."""
    cnt = Counter(c.get("pcf_class") or "blank" for c in crashes)
    cats = sorted((k for k in cnt if k not in pcf.OTHER), key=lambda k: (-cnt[k], k))
    order = cats + [k for k in pcf.OTHER if cnt[k]]
    keyed = [{**c, "_pcf": c.get("pcf_class") or "blank"} for c in crashes]
    t = _dist(tid, "Primary collision factor category", keyed, "_pcf",
              lambda k: pcf.labels().get(k) or pcf.OTHER.get(k, k), order)
    for r in t["rows"]:
        r["key"] = f"cat_{r['key']}" if r["key"] not in pcf.OTHER else r["key"]
    return t


def is_vru(c) -> bool:
    """A pedestrian, bicyclist, e-bike or e-scooter rider involved (#136; e-bikes and e-scooters N9, #169).
    Motorcyclists are shown alongside, not counted in."""
    return bool(c.get("ped") or c.get("bike") or c.get("ebike") or c.get("escooter"))


def light_group(c) -> str:
    """Daylight / dusk-dawn / dark with street lights / dark without working street lights / not stated (#136)."""
    t = (c.get("lighting") or "").upper()
    if not t:
        return "not_stated"
    if is_unlit(c):
        return "dark_unlit"
    if is_dark(c):
        return "dark_lit"
    return "dusk_dawn" if "DUSK" in t or "DAWN" in t else "daylight" if "DAYLIGHT" in t else "not_stated"


LIGHT_GROUPS = [("daylight", "Daylight"), ("dusk_dawn", "Dusk or dawn"), ("dark_lit", "Dark, street lights on"),
                ("dark_unlit", "Dark, no street lights or not working"), ("not_stated", "Not stated")]


def _t19_mark(group: int, crashes: int, ksi_all: int) -> dict:
    """T19's shares have three bases (#271): the group's crashes (KSI % of group), all crashes and all KSI crashes;
    the mark names each share whose base is under MIN_SHARE_N."""
    parts = [name for name, base in (("KSI % of group", group), ("share of crashes", crashes), ("share of KSI", ksi_all))
             if 0 < base < MIN_SHARE_N]
    return {"small_base": f"{SMALL_MARK}: {', '.join(parts)}"} if parts else {}


def _vru_tables(crashes: list[dict], s: str) -> list[dict]:
    """T19: pedestrian and bicycle crashes, their share of all crashes and of KSI crashes, and how often each group's
    crashes are KSI next to all other crashes ("how dangerous", #136). T20: pedestrian crashes by lighting."""
    n = len(crashes)
    ksi_all = sum(c["severity"] in "KA" for c in crashes)
    groups = [("ped", "Pedestrian crashes", lambda c: bool(c.get("ped"))),
              ("bike", "Bicycle crashes", lambda c: bool(c.get("bike"))),
              ("ebike", "E-bike crashes", lambda c: bool(c.get("ebike"))),
              ("escooter", "E-scooter crashes", lambda c: bool(c.get("escooter"))),
              ("ped_or_bike", "Pedestrian, bicycle, e-bike or e-scooter crashes", is_vru),
              ("motorcycle", "Motorcycle crashes", lambda c: bool(c.get("motorcycle"))),
              ("other", "All other crashes (no pedestrian or bicyclist)", lambda c: not is_vru(c)),
              ("all", "All crashes", lambda c: True)]
    rows = []
    for key, label, f in groups:
        sub = [c for c in crashes if f(c)]
        ksi = sum(c["severity"] in "KA" for c in sub)
        rows.append(_row(key, label, crashes=len(sub), ksi_crashes=ksi, fatal_crashes=sum(c["severity"] == "K" for c in sub),
                         ksi_pct=pct(ksi, len(sub)) if sub else None, share_of_crashes_pct=pct(len(sub), n),
                         share_of_ksi_pct=pct(ksi, ksi_all),
                         **_t19_mark(len(sub), n, ksi_all)))
    t19 = _table(f"T19{s}", "Pedestrians and bicyclists", [
        ("crashes", "Crashes"), ("ksi_crashes", "KSI crashes"), ("fatal_crashes", "Fatal crashes"),
        ("ksi_pct", "KSI % of the group's crashes"), ("share_of_crashes_pct", "Share of all crashes %"),
        ("share_of_ksi_pct", "Share of all KSI crashes %")], rows, crashes)
    peds = [{**c, "_light": light_group(c)} for c in crashes if c.get("ped")]
    t20 = _dist(f"T20{s}", "Pedestrian crashes by lighting", peds, "_light", dict(LIGHT_GROUPS).get,
                [k for k, _ in LIGHT_GROUPS])
    return [t19, t20]


def _movement(m) -> str:
    t = re.sub(r"\s+", " ", str(m or "").strip().upper())
    return {"ENTERING TRAFFICD": "ENTERING TRAFFIC"}.get(t, t)      # CHP's own typo in the code list (#52)


def _at_fault_movement(c: dict) -> str:
    """Movement before the collision of the party at fault (the CHP 555 PCF party); party 1 when none is marked."""
    ps = c.get("parties") or []
    p = next((x for x in ps if x.get("at_fault")), None) or next((x for x in ps if str(x.get("party_number")) == "1"), None)
    return _movement(p.get("movement")) if p else ""


def _safety_tables(crashes: list[dict], s: str) -> list[dict]:
    """The standard safety-section rows that need no method choice (#52): hit-and-run, DUI and speed-related by
    the PCF violation (VC 23152/23153 and 22350, as #52 defines them), pedestrian action, movement of the party
    at fault, and broadside split into left turn vs right angle. Each count is crashes, with KSI and share."""
    n = len(crashes)

    def row(key, label, sub):
        return _row(key, label, crashes=len(sub), ksi_crashes=sum(c["severity"] in "KA" for c in sub),
                    share_pct=pct(len(sub), n))
    vc = lambda c, *secs: any(str(c.get("pcf") or "").startswith(x) for x in secs)
    hr = [c for c in crashes if str(c.get("hit_run") or "").upper() in ("F", "M", "FELONY", "MISDEMEANOR")]
    flags = [row("hit_and_run", "Hit and run (felony or misdemeanor)", hr),
             row("hit_and_run_felony", "  of which felony (injury or death)",
                 [c for c in hr if str(c.get("hit_run")).upper() in ("F", "FELONY")]),
             row("dui", "Driving under the influence (PCF VC 23152 / 23153)", [c for c in crashes if vc(c, "23152", "23153")]),
             row("speed", "Unsafe speed (PCF VC 22350)", [c for c in crashes if vc(c, "22350")])]
    cols = [("crashes", "Crashes"), ("ksi_crashes", "KSI crashes"), ("share_pct", "Share %")]
    out = [_table(f"T14{s}", "Hit and run, DUI and speed", cols, flags, crashes)]
    peds = [c for c in crashes if c.get("ped_action") and "NO PEDESTRIAN" not in str(c["ped_action"]).upper()]
    out.append(_dist(f"T15{s}", "Pedestrian action (crashes with a pedestrian action stated)", peds, "ped_action",
                     lambda v: (v or "Not stated").capitalize()))
    for c in crashes:
        c["_mv"] = _at_fault_movement(c)
    out.append(_dist(f"T16{s}", "Movement before the collision (party at fault)", crashes, "_mv",
                     lambda v: (v or "Not stated").capitalize()))
    broad = [c for c in crashes if str(c.get("collision_type") or "").upper() == "BROADSIDE"]
    left = [c for c in broad if any(_movement(p.get("movement")) == "MAKING LEFT TURN" for p in c.get("parties") or [])]
    right = [c for c in broad if c not in left]
    out.append(_table(f"T17{s}", "Broadside crashes: left turn vs right angle (share of broadside)", cols,
                      [_row(k, lbl, crashes=len(sub), ksi_crashes=sum(c["severity"] in "KA" for c in sub),
                            share_pct=pct(len(sub), len(broad)))
                       for k, lbl, sub in (("left_turn", "Left turn (a party was making a left turn)", left),
                                           ("right_angle", "Right angle (no party turning left)", right))], broad))
    for c in crashes:
        c.pop("_mv", None)
    return out


def tables_for(crashes: list[dict], years: int, suffix: str = "", window: list[int] | None = None) -> list[dict]:
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
    out.append(_pcf_categories(f"T18{s}", crashes))
    out.append(_dist(f"T6{s}", "Lighting", crashes, "lighting", lambda v: (v or "Not stated").title()))
    out.append(_dist(f"T7{s}", "Weather", crashes, "weather", lambda v: (v or "Not stated").title()))
    out.append(_dist(f"T8{s}", "Road surface", crashes, "surface", lambda v: (v or "Not stated").title()))
    hd = Counter((c.get("day_of_week"), c.get("hour")) for c in crashes)
    out.append(_table(f"T9{s}", "Crashes by hour and day of week",
                      [(str(h), f"{h:02d}") for h in range(24)] + [("unknown_hour", "Hour not stated")],
                      [_row(d, d, **{str(h): hd[(d, h)] for h in range(24)},
                            unknown_hour=sum(v for (dd, h), v in hd.items() if dd == d and h is None)) for d in DOW]
                      # a crash with no day stated keeps its own row, so T9 adds up to the crashes (#52)
                      + ([_row("not_stated", "Day not stated", **{str(h): hd[(dd, h)] for h in range(24) for dd in [None]},
                               unknown_hour=hd[(None, None)])] if any(c.get("day_of_week") not in DOW for c in crashes) else []),
                      crashes))
    # the same crashes by hour and by day, each severity-stacked (#269): every bar on tab 3 is one of these cells
    hrs = [{**c, "_hr": "" if c.get("hour") is None else str(c["hour"])} for c in crashes]
    out.append(_dist(f"T26{s}", "Crashes by hour of day", hrs, "_hr", lambda v: f"{int(v):02d}" if v else "Hour not stated",
                     [str(h) for h in range(24)] + ([""] if any(c["_hr"] == "" for c in hrs) else [])))
    days = [{**c, "_day": c.get("day_of_week") if c.get("day_of_week") in DOW else ""} for c in crashes]
    out.append(_dist(f"T27{s}", "Crashes by day of week", days, "_day", lambda v: v or "Day not stated",
                     DOW + ([""] if any(c["_day"] == "" for c in days) else [])))
    rows = []
    for key, label in MODES:
        sub = [c for c in crashes if c.get(key)]
        rows.append(_row(key, label, crashes=len(sub), ksi_crashes=sum(c["severity"] in "KA" for c in sub),
                         share_pct=pct(len(sub), n)))
    out.append(_table(f"T10{s}", "Road users involved", [("crashes", "Crashes"), ("ksi_crashes", "KSI crashes"),
                                                         ("share_pct", "Share %")], rows, crashes))
    out += _safety_tables(crashes, s)
    out += _vru_tables(crashes, s)
    yr = Counter(c.get("year") for c in crashes)
    # every year of the window, zero years included, so a trend never hides a quiet year (#104); injury / property
    # damage split, CHP's preliminary reports and the COVID years (2020-21, docs/03 #34 item 13) per year
    ys = sorted(set(window or []) | {k for k in yr if k is not None})
    rows = []
    for y in ys:
        cy = [c for c in crashes if c.get("year") == y]
        rows.append(_row(y, str(y), crashes=len(cy), ksi_crashes=sum(c["severity"] in "KA" for c in cy),
                         injury_crashes=sum(c["severity"] in INJURY for c in cy),
                         pdo_crashes=sum(c["severity"] == "O" for c in cy),
                         preliminary=sum(bool(c.get("preliminary")) for c in cy),
                         covid="Yes" if y in study_mod.COVID_YEARS else "No",
                         **{f"sev_{lvl.lower()}": sum(c["severity"] == lvl for c in cy) for lvl in "KABCUO"}))
    out.append(_table(f"T11{s}", "Crashes by year", [("crashes", "Crashes"), ("ksi_crashes", "KSI crashes"),
                                                     ("injury_crashes", "Injury crashes"), ("pdo_crashes", "Property damage only"),
                                                     ("preliminary", "Preliminary reports"), ("covid", "COVID year"),
                                                     ("sev_k", "Fatal (K)"), ("sev_a", "Serious (A)"), ("sev_b", "Minor (B)"),
                                                     ("sev_c", "Possible (C)"), ("sev_u", "Injury, level not stated"),
                                                     ("sev_o", "Property damage (O)")],
                      rows, crashes))
    return out


CRITICAL_K = 1.645          # 95% confidence (PIARC: 1.036 85%, 1.282 90%, 1.645 95%, 2.326 99%)
CRITICAL_MIN_SITES = 3      # a reference average needs at least this many similar sites with exposure


def exposure(kind: str, years: float, aadt_or_tev: float | None, length_mi: float | None = None) -> float | None:
    """Exposure in the units the rate uses: MEV for intersections, 100M VMT for segments (HSM Ch. 4)."""
    if not aadt_or_tev or not years:
        return None
    if kind == "intersection":
        return aadt_or_tev * 365 * years / 1e6
    return aadt_or_tev * 365 * years * length_mi / 1e8 if length_mi else None


def critical_rates(sites: list[tuple[str, int, float]], k: float = CRITICAL_K) -> tuple[float | None, dict]:
    """sites = (id, crashes, exposure) of one kind. Returns (reference average rate, {id: critical rate}).
    Critical rate = Ra + K·sqrt(Ra / E) + 1 / (2E), Ra = Σ crashes / Σ exposure (HSM Ch. 4 critical rate method)."""
    use = [s for s in sites if s[2]]
    if len(use) < CRITICAL_MIN_SITES:
        return None, {}
    ra = sum(n for _, n, _ in use) / sum(e for _, _, e in use)
    return ra, {lid: ra + k * math.sqrt(ra / e) + 1 / (2 * e) for lid, _, e in use}


def _counts(crashes):
    sev = Counter(c["severity"] for c in crashes)
    return {"crashes": len(crashes), "ksi_crashes": sev["K"] + sev["A"], "fatal_crashes": sev["K"],
            "injury_crashes": sum(sev[k] for k in INJURY), "pdo_crashes": sev["O"],
            "killed": sum(c.get("killed", 0) for c in crashes), "injured": sum(c.get("injured", 0) for c in crashes),
            "dark_crashes": sum(is_dark(c) for c in crashes), "ped_crashes": sum(bool(c.get("ped")) for c in crashes),
            "bike_crashes": sum(bool(c.get("bike")) for c in crashes),
            "ebike_crashes": sum(bool(c.get("ebike")) for c in crashes),
            "escooter_crashes": sum(bool(c.get("escooter")) for c in crashes),
            "moto_crashes": sum(bool(c.get("motorcycle")) for c in crashes),
            "vru_crashes": sum(is_vru(c) for c in crashes),
            "vru_ksi_crashes": sum(is_vru(c) and c["severity"] in "KA" for c in crashes)}


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


def unplaced_text(n: int, share_pct, ksi: int, limitation: bool) -> str:
    """The unplaced-crashes caveat, singular or plural by count (#266)."""
    one = n == 1
    text = (f"{n} crash{'' if one else 'es'} on this corridor ({share_pct}%) "
            f"{'has' if one else 'have'} no coordinates and {'is' if one else 'are'}n't placed yet")
    if ksi:
        text += f", including {ksi} fatal or serious-injury crash{'' if ksi == 1 else 'es'} not in the KSI count"
    return text + (". This is a data limitation for this study." if limitation else ".")


def approximate_text(n: int) -> str:
    """The approximate-freeway caveat, singular or plural by count (#266)."""
    one = n == 1
    return (f"{n} freeway crash{' has' if one else 'es have'} no usable GPS and {'is' if one else 'are'} placed "
            "approximately (usually within 0.5 mi) from the report's description. "
            f"{'It counts' if one else 'They count'} on the corridor segments, never at an intersection, so intersection "
            f"tables and collision diagrams leave {'it' if one else 'them'} out.")


def gps_far_text(n: int, check_ft: float) -> str:
    """The GPS-far-from-stated caveat, singular or plural by count (#266)."""
    one = n == 1
    return (f"{n} crash{' has' if one else 'es have'} a GPS point more than {check_ft:g} ft (plus the reported distance) "
            f"from the intersection named in the report. {'It is' if one else 'They are'} counted where the GPS puts "
            f"{'it' if one else 'them'}; check {'it' if one else 'them'} on the map.")


def mainline_groups(net: dict, placed: list[dict], radius_ft: float) -> tuple[dict, dict]:
    """({segment id: its mainline crashes}, {crash id: (rate class, reason)}) on a state-highway corridor (#304,
    rate_class.py). A mainline crash at a study intersection counts in the segment on its GPS side (answer 2a)."""
    from . import rate_class
    cls = {c["crash_id"]: rate_class.classify(c, net, radius_ft) for c in placed}
    its = {i["id"]: i for i in net.get("intersections", [])}
    line = Polyline([tuple(p) for p in net["line"]]) if net.get("line") else None
    out: dict[str, list] = {}
    for c in placed:
        if cls[c["crash_id"]][0] != rate_class.MAINLINE:
            continue
        sid = c["location_id"]
        if c["kind"] == "intersection" and sid in its:
            st = line.project(c["lat"], c["lon"]).station_ft \
                if line is not None and c.get("lat") is not None and c.get("lon") is not None else None
            sid = rate_class.segment_for(its[sid], net.get("segments", []), st)
        out.setdefault(sid, []).append(c)
    return out, cls


def shs_rate_tables(net: dict, years: list[int], placed: list[dict], radius_ft: float,
                    ramp_out: list[dict] = ()) -> list[dict]:
    """T22 / T23: crash rates on a state-highway corridor from Caltrans AADT (#287; user decision 2026-10-26).
    Crashes per million vehicle-miles: all, fatal + injury (K, A, B, C and injury level not stated) and fatal, per
    study segment with Caltrans exposure for every window year; each against the corridor's own average (crashes over
    vehicle-miles of the segments that have rates), and the corridor's rate year by year. Every row carries the count
    years and source. The entered AADT (T2) is untouched. Mainline crashes only (#304, user decision #297)."""
    vols = net.get("shs_volumes") or {}
    if not vols:
        return []
    segs = {s["id"]: s for s in net.get("segments", [])}
    groups, cls = mainline_groups(net, placed, radius_ft)
    fi = lambda cs: sum(c["severity"] in "KABCU" for c in cs)                       # noqa: E731
    rows, mvm_y, crashes_y, fi_y, mvm_of = [], Counter(), Counter(), Counter(), {}
    for sid, v in vols.items():
        s = segs.get(sid)
        if s is None or not years or any(v["by_year"].get(y) is None for y in years):
            continue
        cs = groups.get(sid, [])
        per_year = {y: v["by_year"][y] * s["length_mi"] * 365 / 1e6 for y in years}
        mvm = mvm_of[sid] = sum(per_year.values())
        for y in years:
            mvm_y[y] += per_year[y]
            crashes_y[y] += sum(c.get("year") == y for c in cs)
            fi_y[y] += fi([c for c in cs if c.get("year") == y])
        rows.append(_row(sid, s["name"], crashes=len(cs), fi_crashes=fi(cs), fatal_crashes=sum(c["severity"] == "K" for c in cs),
                         length_mi=round(s["length_mi"], 3), aadt=round(sum(v["by_year"][y] for y in years) / len(years)),
                         mvm=round(mvm, 2), rate_all=r2(len(cs) / mvm) if mvm else None,
                         rate_fi=r2(fi(cs) / mvm) if mvm else None,
                         rate_fatal=r2(sum(c["severity"] == "K" for c in cs) / mvm) if mvm else None,
                         count_years=v["count_years"], source=v["source"]))
    if not rows:
        return []
    tot_c, tot_m = sum(r["values"]["crashes"] for r in rows), sum(mvm_of[r["key"]] for r in rows)
    avg = r2(tot_c / tot_m) if tot_m else None
    for r in rows:
        r["values"].update(corridor_rate_all=avg, ratio_to_corridor=r2(r["values"]["rate_all"] / avg)
                           if avg and r["values"]["rate_all"] is not None else None)
        # small numbers (docs/03, #271): a rate on fewer than MIN_SHARE_N crashes is kept and marked; the screen shows
        # the count only, "too few to compare"; so is a ratio to an average built on too few
        small = [x for x, n in (("segment", r["values"]["crashes"]), ("corridor average", tot_c)) if n < MIN_SHARE_N]
        if small:
            r["values"]["small_base"] = f"{SMALL_MARK}: {', '.join(small)}"
    on = [c for sid in (r["key"] for r in rows) for c in groups.get(sid, [])]
    cols = [("crashes", "Crashes"), ("fi_crashes", "Fatal + injury crashes"), ("fatal_crashes", "Fatal crashes"),
            ("length_mi", "Length (mi)"), ("aadt", "AADT (window average)"), ("mvm", "Million vehicle-miles"),
            ("rate_all", "Crashes per MVM"), ("rate_fi", "Fatal + injury per MVM"), ("rate_fatal", "Fatal per MVM"),
            ("corridor_rate_all", "Corridor average per MVM"), ("ratio_to_corridor", "Rate ÷ corridor average"),
            ("count_years", "AADT count years"), ("source", "AADT source")]
    t22 = _table("T22", "State-highway crash rates (Caltrans AADT; crashes per million vehicle-miles)", cols, rows, on)
    # which crashes count (#304, user decision #297): mainline only; ramps are rated in T25, cross streets in none
    n_cls = Counter(k for k, _ in cls.values())
    n_ramp, n_cross = n_cls["ramp"] + len(ramp_out), n_cls["cross_street"]
    unrated = n_cls["mainline"] - tot_c                       # mainline crashes on segments without Caltrans counts
    t22["scope"] = {"rated_crashes": tot_c, "unrated_mainline_crashes": unrated, "ramp_crashes": n_ramp,
                    "cross_street_crashes": n_cross,
                    "corridor_rate_all": avg, "small": tot_c < MIN_SHARE_N,
                    "classes": {cid: list(v) for cid, v in cls.items()},
                    "text": f"Mainline crashes: {tot_c}"
                            + (f" ({unrated} more on segments without Caltrans counts)" if unrated else "")
                            + f". Not in this rate: {n_ramp} ramp crash"
                            f"{'es' if n_ramp != 1 else ''} (see Ramps), {n_cross} cross-street crash"
                            f"{'es' if n_cross != 1 else ''}."}
    t24 = _truck_rates(vols, segs, groups, years)
    yrows = [_row(y, str(y), crashes=crashes_y[y], fi_crashes=fi_y[y], mvm=round(mvm_y[y], 2),
                  rate_all=r2(crashes_y[y] / mvm_y[y]) if mvm_y[y] else None,
                  rate_fi=r2(fi_y[y] / mvm_y[y]) if mvm_y[y] else None,
                  **({"small_base": SMALL_MARK} if crashes_y[y] < MIN_SHARE_N else {})) for y in years]
    t23 = _table("T23", "State-highway crash rate by year (the segments in T22)",
                 [("crashes", "Crashes"), ("fi_crashes", "Fatal + injury crashes"), ("mvm", "Million vehicle-miles"),
                  ("rate_all", "Crashes per MVM"), ("rate_fi", "Fatal + injury per MVM")], yrows, on)
    return [t22, t23, *([t24] if t24 else [])]


def _truck_rates(vols: dict, segs: dict, groups: dict, years: list[int]) -> dict | None:
    """T24: heavy-truck-involved crashes (docs/03 heavy truck) per million 3+ axle truck-miles, per segment with truck
    AADT for every window year, against the corridor's own truck average; the small-number rule as T22."""
    rows, mvm_of = [], {}
    for sid, v in vols.items():
        s, tb = segs.get(sid), v.get("trucks_by_year") or {}
        if s is None or not years or any(tb.get(y) is None for y in years):
            continue
        cs = [c for c in groups.get(sid, []) if c.get("heavy_truck")]
        mvm = mvm_of[sid] = sum(tb[y] * s["length_mi"] * 365 / 1e6 for y in years)
        rows.append(_row(sid, s["name"], truck_crashes=len(cs), length_mi=round(s["length_mi"], 3),
                         trucks_3plus=round(sum(tb[y] for y in years) / len(years)), truck_mvm=round(mvm, 2),
                         rate_truck=r2(len(cs) / mvm) if mvm else None,
                         count_years=v.get("truck_count_years", ""), source=v["source"]))
    if not rows:
        return None
    tot_c, tot_m = sum(r["values"]["truck_crashes"] for r in rows), sum(mvm_of[r["key"]] for r in rows)
    avg = r2(tot_c / tot_m) if tot_m else None
    for r in rows:
        v = r["values"]
        v.update(corridor_rate_truck=avg, ratio_to_corridor=r2(v["rate_truck"] / avg)
                 if avg and v["rate_truck"] is not None else None)
        small = [x for x, n in (("segment", v["truck_crashes"]), ("corridor average", tot_c)) if n < MIN_SHARE_N]
        if small:
            v["small_base"] = f"{SMALL_MARK}: {', '.join(small)}"
    on = [c for r in rows for c in groups.get(r["key"], []) if c.get("heavy_truck")]
    t = _table("T24", "State-highway truck-involved crash rates (Caltrans 3+ axle truck AADT; per million truck-miles)",
               [("truck_crashes", "Heavy-truck-involved crashes"), ("length_mi", "Length (mi)"),
                ("trucks_3plus", "3+ axle truck AADT (window average)"), ("truck_mvm", "Million truck-miles"),
                ("rate_truck", "Truck-involved crashes per million truck-miles"),
                ("corridor_rate_truck", "Corridor average"), ("ratio_to_corridor", "Rate ÷ corridor average"),
                ("count_years", "Truck AADT count years"), ("source", "AADT source")], rows, on)
    t["scope"] = {"rated_crashes": tot_c, "corridor_rate_truck": avg, "small": tot_c < MIN_SHARE_N,
                  "text": "Crashes involving a heavy truck (which can include trucks under 3 axles) per million miles "
                          "driven by trucks with 3 or more axles."}
    return t


def ramp_rate_tables(net: dict, placed: list[dict], years: list[int]) -> list[dict]:
    """T25: crashes per million vehicles on each identified Caltrans ramp (#287 ramps; user decision 2026-10-30,
    docs/03, #300). A window year's ramp ADT is the latest count at or before it, never a later one, and no more than
    RAMP_MAX_AGE years old (user decision 2026-11-01); a ramp without one for some window year has counts only. The
    scope line counts every ramp crash's outcome."""
    from .aadt import SOURCE, AadtCache
    found = net.get("shs_ramps") or {}
    mine = [c for c in placed if c["crash_id"] in found]
    if not mine or not years:
        return []
    by_ramp, outcome, why = {}, Counter(), Counter()
    for c in mine:
        f = found[c["crash_id"]]
        outcome[f["status"]] += 1
        if f["status"] == "identified":
            by_ramp.setdefault(f["ramp"]["id"], (f["ramp"], []))[1].append(c)
        elif f["status"] == "none":
            why[f["why"]] += 1
    fi = lambda cs: sum(c["severity"] in "KABCU" for c in cs)                       # noqa: E731
    rows = []
    for rid, (ramp, cs) in sorted(by_ramp.items(), key=lambda kv: kv[1][0]["pm"]):
        used = {y: AadtCache.ramp_adt(ramp, y) for y in years}
        mv = sum(u["adt"] * 365 for u in used.values()) / 1e6 \
            if all(u and u["adt"] is not None for u in used.values()) else None
        rows.append(_row(rid, ramp["description"], crashes=len(cs), fi_crashes=fi(cs),
                         picked=sum(found[c["crash_id"]].get("picked", False) for c in cs),
                         postmile=f"{ramp['county']}-{ramp['route']}{ramp.get('route_suffix') or ''} PM "
                                  f"{ramp.get('prefix') or ''}{ramp['pm']:.3f}{ramp.get('suffix') or ''}",
                         adt=round(sum(u["adt"] for u in used.values()) / len(years)) if mv else None,
                         mv=round(mv, 2) if mv else None, rate_all=r2(len(cs) / mv) if mv else None,
                         rate_fi=r2(fi(cs) / mv) if mv else None, count_years=_ramp_years(used),
                         source=f"{SOURCE}, District {int(ramp['district'] or 0)} ramp ADT",
                         **({"small_base": SMALL_MARK} if len(cs) < MIN_SHARE_N else {})))
    t = _table("T25", "Ramp crash rates (Caltrans ramp ADT; crashes per million vehicles)",
               [("crashes", "Crashes"), ("fi_crashes", "Fatal + injury crashes"), ("postmile", "Ramp postmile"),
                ("adt", "Ramp ADT (window average)"), ("mv", "Million vehicles"), ("rate_all", "Crashes per MV"),
                ("rate_fi", "Fatal + injury per MV"), ("count_years", "Ramp count years"),
                ("picked", "Crashes on a ramp the engineer picked"), ("source", "ADT source")], rows,
               [c for _, cs in by_ramp.values() for c in cs])
    n, k, pk, no = len(mine), outcome["identified"], outcome["pick"], outcome["none"]
    reasons = "; ".join(f"{w}: {m}" for w, m in why.most_common())
    t["scope"] = {"ramp_crashes": n, "identified": k, "pick": pk, "none": no, "none_why": dict(why),
                  "text": f"{n} ramp crash{'es' if n != 1 else ''}: {k} on an identified Caltrans ramp; {pk} with 2 or "
                          f"more possible ramps (the engineer picks); {no} with no ramp rate"
                          + (f" ({reasons})" if reasons else "") + "."}
    return [t]


def _ramp_years(used: dict) -> str:
    """'2021–2023 (2024, 2025 use 2023)': the count years a ramp row uses, and any window year without one."""
    have = {y: u["count_year"] for y, u in used.items() if u and not u.get("too_old")}
    cys = sorted(set(have.values()))
    run = lambda xs: (f"{xs[0]}–{xs[-1]}" if len(xs) > 1 and xs == list(range(xs[0], xs[-1] + 1))  # noqa: E731
                      else ", ".join(map(str, xs)))
    text = run(cys) if cys else ""
    late = {}
    for y, cy in sorted(have.items()):
        if cy != y:
            late.setdefault(cy, []).append(y)
    if late:
        text += " (" + "; ".join(f"{', '.join(map(str, ys))} use{'s' if len(ys) == 1 else ''} {cy}"
                                 for cy, ys in late.items()) + ")"
    old = {}
    for y, u in sorted(used.items()):
        if u and u.get("too_old"):
            old.setdefault(u["count_year"], []).append(y)
    if old:
        text += "; count too old for " + "; ".join(f"{', '.join(map(str, ys))} (newest {cy})" for cy, ys in old.items())
    gone = [y for y, u in used.items() if not u]
    if gone:
        text += f"; no count at or before {', '.join(map(str, gone))}"
    return text.lstrip("; ")


def build(study: dict, net: dict, pull: dict, assignment: dict, exclude: set[str] | None = None) -> dict:
    exclude = exclude or set()
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    placed, unmatched, excluded_n, excluded_prov, gps_far = [], [], 0, 0, 0
    ramp_out = []         # named-ramp crashes the freeway rules exclude (rule "ramp"): still rated in T25 (#314)
    for a in assignment["assignments"]:
        c = {**by_id[a["crash_id"]], **{k: a[k] for k in ("kind", "location_id", "location_provenance")}}
        prov = c["location_provenance"] or ""
        if any(prov.startswith(e) for e in exclude):
            excluded_prov += 1      # counted in T1 so the rows still add up to the pull (#53)
            continue
        if a.get("gps_check") and a["kind"] in ("intersection", "segment"):
            gps_far += 1
        if a["kind"] in ("intersection", "segment"):
            placed.append(c)
        elif a["kind"] == "unmatched":
            unmatched.append(c)
        else:
            excluded_n += 1
            if a.get("rule") == "ramp":
                ramp_out.append(c)
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
        _row("fatal_unplaced", "Of these, fatal crashes without a location (review list, first)",
             value=sum(1 for c in unmatched if c.get("severity") == "K" or (c.get("killed") or 0) > 0)),
        _row("user_placed", "Crashes placed by you (review list; included in Crashes)",
             value=sum(1 for c in placed if c.get("location_provenance") == "user")),
        # how the counted crashes were located (#104 data-quality strip): GPS + exact + other tiers + you = Crashes
        _row("located_gps", "Located by the officer's GPS",
             value=sum(1 for c in placed if c.get("location_provenance") in ("gps", "gps_dms_corrected",
                                                                                 "gps_sign_corrected", "gps_offset_applied"))),
        # the longitude's lost minus restored (#247); already in located_gps
        _row("located_gps_sign", "Of these, GPS whose longitude had lost its minus sign",
             value=sum(1 for c in placed if c.get("location_provenance") == "gps_sign_corrected")),
        # GPS at the named intersection while the report states a distance from it: moved by it (#218); in located_gps
        _row("located_gps_offset", "Of these, GPS moved by the distance and direction the report states",
             value=sum(1 for c in placed if c.get("location_provenance") == "gps_offset_applied")),
        # a default / dispatch point or coarse coordinates aren't a location (#218): placed by street names instead
        _row("gps_ignored", "GPS not used (a default point shared by many reports, or coarse); placed by street names",
             value=sum(1 for c in placed + unmatched if c.get("gps_ignored"))),
        # of which written as degrees-minutes-seconds and converted (#143); already in located_gps
        _row("located_gps_dms", "Of these, GPS converted from degrees-minutes-seconds",
             value=sum(1 for c in placed if c.get("location_provenance") == "gps_dms_corrected")),
        _row("located_fars", "Fatal crashes placed at their FARS point (NHTSA)",
             value=sum(1 for c in placed if c.get("location_provenance") == "fars")),
        _row("located_exact", "Placed by exact street-name match",
             value=sum(1 for c in placed if c.get("location_provenance") == "exact")),
        # the report's two streets can meet at only one place (#203); auto-placed since the user's decision 2026-10-22
        _row("located_unique_pair", "Placed where the report's two streets meet at only one place (a direction or "
             "suffix the report leaves out may differ)",
             value=sum(1 for c in placed if c.get("location_provenance") == "unique_pair")),
        # a name 1-2 letters off one map street, confirmed by its cross street (#233); auto-places only on the user's OK
        _row("located_verified_typo", "Placed after correcting a small typo in a street name (one possible street, "
             "confirmed by the cross street)",
             value=sum(1 for c in placed if c.get("location_provenance") == "verified_typo")),
        # freeway crashes placed by the report (#246, D1): crossing + offset, ramp terminal, connector; gated
        _row("located_freeway", "Freeway crashes with no usable GPS, placed approximately (usually within 0.5 mi) by the "
             "report: where the reference street crosses, the ramp terminal, or along the connector, plus the stated "
             "distance. Counted on segments only",
             value=sum(1 for c in placed if c.get("location_provenance") in ("approximate", "freeway_offset"))),
        _row("located_other", "Placed by other matching tiers (relaxed, near, fuzzy, Jev)",
             value=sum(1 for c in placed if c.get("location_provenance") not in ("gps", "gps_dms_corrected", "gps_sign_corrected", "gps_offset_applied", "fars", "exact",
                                                                                 "unique_pair", "verified_typo", "freeway_offset", "approximate", "user"))),
        # placed by street names using a name or road only Census TIGER/Line has (#229); already in the rows above
        _row("located_tiger", "Of the crashes placed by street names, placed with a street name or road only "
             "TIGER/Line has", value=sum(1 for c in placed if c.get("placed_on") == "tiger")),
        # a road name read through a user-approved alias of its city (#235); already in the rows above
        _row("located_alias", "Of the crashes counted, those whose street name was read through an approved alias",
             value=sum(1 for c in placed if c.get("aliases_used"))),
        _row("excluded", "Crashes outside the study area", value=excluded_n),
    ]
    if exclude:
        summary_rows.append(_row("excluded_provenance", "Crashes left out by placement method", value=excluded_prov))
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
    # Volumes as the engineer entered them: daily AADT, or peak-hour counts converted with the K factor
    peak = study.get("volume_basis") == "peak_hour"
    kf = study.get("k_factor") or 0.10
    daily = (lambda v: v / kf if v is not None else None) if peak else (lambda v: v)
    rates_any = False
    loc_rows = []
    expo: dict[str, tuple[str, int, float | None, float | None]] = {}   # id -> (kind, crashes, exposure, rate)
    for kind, lid, _ in order:
        cs = groups.get(lid, [])
        k = _counts(cs)
        sev = Counter(c["severity"] for c in cs)
        vals = {"kind": kind, **{x: k[x] for x in ("crashes", "ksi_crashes", "fatal_crashes", "injury_crashes",
                                                   "dark_crashes", "ped_crashes", "bike_crashes", "ebike_crashes",
                                                   "escooter_crashes", "moto_crashes", "vru_crashes", "vru_ksi_crashes")},
                **{f"sev_{lvl.lower()}": sev[lvl] for lvl in "KABCUO"},   # the ranking's severity bar (#103)
                "crashes_per_year": r2(k["crashes"] / years) if years else None}
        if kind == "segment":
            s = seg_by[lid]
            seg_aadt = daily(s.get("aadt"))
            rate = segment_rate(k["crashes"], years, seg_aadt, s["length_mi"])
            expo[lid] = (kind, k["crashes"], exposure(kind, years, seg_aadt, s["length_mi"]), rate)
            vals.update(**crash_cost.location_cost(cs, "segment", None))         # LRSM crash cost (#273)
            vals.update(length_mi=round(s["length_mi"], 3),
                        crashes_per_mi_yr=r2(k["crashes"] / s["length_mi"] / years) if years and s["length_mi"] else None,
                        aadt=round(seg_aadt) if seg_aadt is not None else None, rate=r2(rate),
                        rate_unit="per 100M VMT" if rate is not None else None)
            label = s["name"]
        else:
            it = names[lid]
            maj, mnr = daily(it.get("major_aadt")), daily(it.get("minor_aadt"))
            rate = intersection_rate(k["crashes"], years, maj, mnr, it.get("legs"))
            tev = entering_volume(maj, mnr, it.get("legs"))
            expo[lid] = (kind, k["crashes"], exposure(kind, years, tev), rate)
            vals.update(**crash_cost.location_cost(cs, "intersection", it["control"]))
            vals.update(length_mi=None, crashes_per_mi_yr=None, control=it["control"], rate=r2(rate),
                        rate_unit="per MEV" if rate is not None else None)
            label = it["name"]
        rates_any |= rate is not None
        loc_rows.append(_row(lid, label, **vals))
    # Critical rates: each location against the average rate of the corridor's own sites of the same kind (#34 item 7)
    critical = {}
    for kind in ("intersection", "segment"):
        ra, rc = critical_rates([(lid, n, e) for lid, (kd, n, e, _) in expo.items() if kd == kind])
        critical[kind] = {"reference_rate": ra, "sites": sum(1 for kd, _, e, _ in expo.values() if kd == kind and e)}
        for r in loc_rows:
            if r["key"] in rc:
                rate = expo[r["key"]][3]
                r["values"].update(critical_rate=r2(rc[r["key"]]), reference_rate=r2(ra),
                                   over_critical="Yes" if rate > rc[r["key"]] else "No",
                                   rate_to_critical=r2(rate / rc[r["key"]]) if rc[r["key"]] else None)
    for r in loc_rows:
        r["values"].setdefault("critical_rate", None)
        r["values"].setdefault("reference_rate", None)
        r["values"].setdefault("over_critical", None)
        r["values"].setdefault("rate_to_critical", None)
    tables.append(_table("T2", "Locations (corridor order)", [
        ("crashes", "Crashes"), ("crashes_per_year", "Per year"), ("ksi_crashes", "KSI"), ("fatal_crashes", "Fatal"),
        ("injury_crashes", "Injury"), ("dark_crashes", "Dark"), ("ped_crashes", "Ped"), ("bike_crashes", "Bike"), ("ebike_crashes", "E-bike"),
        ("escooter_crashes", "E-scooter"), ("moto_crashes", "Motorcycle"),
        ("vru_crashes", "Ped, bike, e-bike, e-scooter"), ("vru_ksi_crashes", "Of these, KSI"),
        ("length_mi", "Length (mi)"), ("crashes_per_mi_yr", "Per mile per year"), ("rate", "Rate"),
        ("reference_rate", "Average rate, similar sites"), ("critical_rate", "Critical rate (95%)"),
        ("over_critical", "Over critical rate?"), ("rate_to_critical", "Rate ÷ critical rate"),
        ("sev_k", "Fatal (K)"), ("sev_a", "Serious (A)"), ("sev_b", "Minor (B)"), ("sev_c", "Possible (C)"),
        ("sev_u", "Injury, level not stated"), ("sev_o", "Property damage (O)"),
        ("crash_cost", "Crash cost ($, Caltrans LRSM 2026)"), ("cost_control_unknown", "Cost: intersection control unknown")],
        loc_rows, placed))
    tables[-1]["source_note"] = crash_cost.SOURCE                     # the crash-cost basis (#273)
    shs_tables = shs_rate_tables(net, [y for y in pull["years"] if y not in years_missing], placed,
                                 study.get("radius_ft") or 250, ramp_out)
    shs_tables += ramp_rate_tables(net, placed + ramp_out, [y for y in pull["years"] if y not in years_missing])
    tables += shs_tables
    # T13: collision type x location (#105 grid): one row per T2 location, one column per collision type with crashes
    tcount = Counter((c.get("collision_type") or "") for c in placed)
    types = sorted(tcount, key=lambda k: (-tcount[k], k))
    grid_rows = []
    for r in loc_rows:
        cs = groups.get(r["key"], [])
        n = Counter((c.get("collision_type") or "") for c in cs)
        grid_rows.append(_row(r["key"], r["label"], **{(k or "not_stated"): n[k] for k in types}, total=len(cs)))
    t13 = _table("T13", "Collision type by location", [((k or "not_stated"), (k or "Not stated").title()) for k in types]
                 + [("total", "All types")], grid_rows, placed)
    tables_after_t12 = [t13]
    tables += tables_for(placed, years, window=[y for y in pull["years"] if y not in years_missing])
    from . import signals as signals_mod          # C7; imported here because signals imports this module
    scr = signals_mod.screen(placed, [(r["key"], r["label"]) for r in loc_rows])
    tables.append(scr["table"])
    tables += tables_after_t12

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
                        "text": unplaced_text(len(unmatched), pct(len(unmatched), total_known),
                                              sum(c["severity"] in ("K", "A") for c in unmatched), share > UNPLACED_LIMIT)})
    approx = sum(1 for c in placed if c.get("location_provenance") == "approximate")
    if approx:                             # #255: say what the precise-point analyses leave out
        caveats.append({"key": "approximate_freeway", "count": approx,
                        "text": approximate_text(approx)})
    u = sum(c["severity"] == "U" for c in placed)
    if u:
        caveats.append({"key": "injury_level_unknown", "count": u,
                        "text": f"{u} injury crash{'es have' if u != 1 else ' has'} no reported injury level, so KSI may be undercounted."})
    notes = missing_notes(missing_detail(pull, placed + unmatched))
    for k in ("parties", "iwp"):
        if k in notes:
            caveats.append({"key": f"{k}_missing", "text": notes[k], "limitation": True})
    annotate(tables, notes)
    if years_missing:
        caveats.append({"key": "years_missing", "years": years_missing,
                        "text": f"CCRS has no queryable data for {', '.join(map(str, years_missing))}; those years are not in the profile."})
    from .shs import corridor_routes
    if shs_tables:
        tids = ", ".join(t["id"] for t in shs_tables)
        trucks = " (T24: heavy-truck-involved crashes over 3+ axle truck AADT)" if "T24" in tids else ""
        caveats.append({"key": "shs_rates", "text": f"State-highway crash rates ({tids}) use Caltrans Traffic Census "
                        f"AADT{trucks}; each row names its count years. They count crashes as CrashIQ places them on the "
                        "corridor, not by Caltrans' on-highway rule, so they are not comparable with Caltrans' "
                        "published averages."})
    if not rates_any and not shs_tables:
        routes = sorted(corridor_routes(net))
        vols = net.get("shs_volumes") or {}
        off_pm = bool(vols) and all(v.get("pm_coverage", 1.0) == 0 for v in vols.values())
        why = (" This corridor isn't a state highway, so local traffic counts are needed." if not routes else
               f" Route {', '.join(routes)} isn't in Caltrans' state-highway postmiles here (for example a relinquished "
               "stretch), so Caltrans traffic counts don't apply and local traffic counts are needed." if off_pm else "")
        caveats.append({"key": "rates_not_computed", "text": "Crash rates were not computed (no AADT entered)." + why})
    elif peak:
        caveats.append({"key": "aadt_from_peak_hour", "k_factor": kf,
                        "text": f"AADT was estimated from peak-hour counts (AADT = peak-hour volume / K, K = {kf:.0%})."})
    for kind, c in critical.items():
        if 0 < c["sites"] < CRITICAL_MIN_SITES:
            caveats.append({"key": f"critical_{kind}", "text": f"Critical rates need AADT at {CRITICAL_MIN_SITES} or more "
                            f"{kind}s to form a reference average ({c['sites']} entered)."})
    over = [r for r in loc_rows if r["values"].get("over_critical") == "Yes"]
    if any(c["reference_rate"] is not None for c in critical.values()):
        caveats.append({"key": "critical_rate", "count": len(over),
                        "text": f"Critical rates (95% confidence) compare each location with the average rate of this "
                                f"corridor's own intersections or segments, not statewide averages. "
                                f"Locations above their critical rate: {len(over)} of "
                                f"{sum(1 for r in loc_rows if r['values'].get('critical_rate') is not None)}."})
    if gps_far:
        caveats.append({"key": "gps_far_from_stated", "count": gps_far,
                        "text": gps_far_text(gps_far, assign_mod.GPS_CHECK_FT)})
    if exclude:
        caveats.append({"key": "excluded_provenance", "text": f"Crashes placed by {', '.join(sorted(exclude))} are left out of this run."})

    prov = Counter(c["location_provenance"] for c in placed)
    prov["unmatched"] = len(unmatched)
    return {"study_id": study["id"], "min_share_n": MIN_SHARE_N,
            "window": {"from_year": study["from_year"], "to_year": study["to_year"],
                                                 "years_with_data": years},
            "kpis": {"crashes": "T1/crashes/value", "ksi_crashes": "T1/ksi_crashes/value",
                     "injury_crashes": "T1/injury_crashes/value", "crashes_per_mi_yr": "T1/crashes_per_mi_yr/value"},
            "tables": tables, "signals": scr["signals"], "screen_tests": scr["tests_run"], "caveats": caveats, "location_provenance": dict(sorted(prov.items())),
            "source": pull["source"], "pulled_at": pull["pulled_at"], "excluded_provenance": sorted(exclude),
            # where approximate freeway placements are counted (#255): the findings say so
            "approximate_locations": sorted({c["location_id"] for c in placed
                                             if c.get("location_provenance") == "approximate" and c.get("location_id")})}


# Tables built from CCRS Parties (road users, trucks, movement, the diagram) or InjuredWitnessPassengers (injury level):
# a year missing from the pull undercounts them silently unless every one of them says so (#188).
PARTY_TABLES = ("T2", "T10", "T16", "T17", "T19", "T20", "T21")
IWP_TABLES = ("T1", "T2", "T3", "T11", "T19")


def missing_detail(pull: dict, crashes: list[dict]) -> dict:
    """{"parties": (years, crashes in those years), "iwp": (...)} for the years whose Parties / IWP table the pull
    didn't have (CHP publishes them later than the Crashes table: Parties 2025 came out on 2026-10-22)."""
    out = {}
    cl = pull.get("cleaning", {})
    for key, field in (("parties", "parties_missing_years"), ("iwp", "iwp_missing_years")):
        ys = sorted(set(cl.get(field) or []))
        if ys:
            out[key] = (ys, sum(1 for c in crashes if c.get("year") in ys))
    # CHP published the file but it isn't in the datastore: the server is downloading it (#196)
    out["downloading"] = {k.split("_")[0] for k in cl.get("files_pending") or {}}
    return out


def missing_notes(missing: dict) -> dict:
    notes = {}
    soon = " CHP has published the file; CrashIQ is downloading it and adds these details on the next refresh."
    if "parties" in missing:
        ys, n = missing["parties"]
        notes["parties"] = (f"No CCRS party details for {', '.join(map(str, ys))} in this pull: road users, heavy trucks, "
                            f"movements and the collision diagram leave out those years' {n} crash{'es' if n != 1 else ''}."
                            + (soon if "parties" in missing.get("downloading", ()) else ""))
    if "iwp" in missing:
        ys, n = missing["iwp"]
        notes["iwp"] = (f"No CCRS injury details for {', '.join(map(str, ys))} in this pull: those years' {n} "
                        f"crash{'es' if n != 1 else ''} with injuries count as 'injury, level not stated' (U), so KSI "
                        "is undercounted." + (soon if "iwp" in missing.get("downloading", ()) else ""))
    return notes


def annotate(tables: list[dict], notes: dict) -> None:
    """Put the missing-year note on every table that depends on the missing CCRS table (#188)."""
    for t in tables:
        base = t["id"].split("@")[0]
        parts = [notes[k] for k, ids in (("parties", PARTY_TABLES), ("iwp", IWP_TABLES)) if k in notes and base in ids]
        if parts:
            t["note"] = " ".join(parts)


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
    from .crashes import aadt_for, postmile_for
    net = with_shs(net, pull, postmile_for(request.app.state), aadt_for(request.app.state))
    return build(study, net, pull, a, {e for e in exclude.split(",") if e})


def with_shs(net: dict, pull: dict, postmiles, aadt_cache) -> dict:
    """The network with Caltrans exposure on a state-highway corridor (#287), when both sources are ready."""
    from . import shs
    years = [y for y in pull["years"] if y not in pull["cleaning"].get("years_missing", [])]
    if not shs.corridor_routes(net):
        return net
    vols = shs.segment_volumes(net, postmiles, aadt_cache, years)
    found = shs.ramp_crashes(pull["crashes"], postmiles, aadt_cache)
    return {**net, **({"shs_volumes": vols} if vols else {}), **({"shs_ramps": found} if found else {})}


def diagram_table(lid: str, diagram: dict, crashes: list[dict]) -> dict:
    """T21: the crashes of the collision diagram, numbered in date order (the numbers on the diagram)."""
    rows = [_row(r["n"], f"{r['date']} {r['hour']:02d}00" if r.get("hour") is not None else str(r["date"]),
                 crash_id=r["crash_id"], approach=r["approach"], type=r["type_label"], severity=r["severity"],
                 code=r["code"]) for r in diagram["crashes"]]
    return _table(f"T21@{lid}", "Collision diagram crashes (number on the diagram; code = road surface + light, HSM)",
                  [("crash_id", "Collision Id"), ("approach", "Approach"), ("type", "Type"), ("severity", "Severity"),
                   ("code", "Code")], rows, crashes)


@router.get("/studies/{sid}/profile/locations/{lid}")
def get_location_profile(sid: str, lid: str, request: Request) -> dict:
    study, net, pull, a = assign_mod.for_study(request.app.state.db, sid)
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    placed = [{**by_id[x["crash_id"]], "location_id": x["location_id"], "location_provenance": x["location_provenance"]}
              for x in a["assignments"] if x["location_id"] == lid]
    years = len(pull["years"]) - len(pull["cleaning"].get("years_missing", []))
    tables = tables_for(placed, years, suffix=f"@{lid}")
    it = next((i for i in net["intersections"] if i["id"] == lid and i.get("is_study")), None)
    diagram = None
    if it is not None and placed:                 # one collision diagram per study intersection (#106, N10)
        from . import diagram as diagram_mod
        diagram = diagram_mod.build(net, it, placed)
        tables.append(diagram_table(lid, diagram, placed))
    annotate(tables, missing_notes(missing_detail(pull, placed)))
    from .crashes import postmile_for
    pm = postmile_for(request.app.state)
    return {"location_id": lid, "min_share_n": MIN_SHARE_N, "tables": tables, "diagram": diagram,
            "crashes": [{**{k: c.get(k) for k in ("crash_id", "date", "hour", "day_of_week", "collision_type", "severity",
                                                  "lighting", "pcf", "primary_road", "secondary_road", "lat", "lon",
                                                  "location_provenance")},
                         **({"postmile": p} if pm is not None and (p := pm.for_crash(c)) else {})} for c in placed]}
