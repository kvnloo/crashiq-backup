"""C3 crash pull: every CCRS crash a corridor study needs, cleaned with logged steps, cached per study.

For each year in the study window (resources resolved at runtime from the CKAN `ccrs` package):
  (a) crashes WITH coordinates inside the corridor's bounding box (+ margin);
  (b) crashes WITHOUT coordinates in the same cities whose PrimaryRoad or SecondaryRoad normalizes to the
      corridor street (they are placed later, C4; until then #10 counts them as `unmatched`);
then Parties and InjuredWitnessPassengers joined by Collision Id. Cleaning steps are counted, never silent.
"""

from __future__ import annotations

import csv
import functools
import hashlib
import json
import math
import threading
import urllib.parse
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from . import grade
from . import network as network_mod
from . import study as study_mod
from .db import Database
from .geo import LocalProjection, Polyline
from .names import ROUTE_SPELLINGS, drop_directional, route_number, route_numbers, same_core, street_key
from .sources import ca_ccrs as cc
from .sources.ckan import Ckan, CkanError

PAGE = 5000
ID_CHUNK = 500          # Collision Ids per Parties/IWP query, at most
MAX_URL_SQL = 6000      # data.ca.gov takes the SQL in the URL: longer than ~8 KB is HTTP 414 (Pasadena, #113). The
                        # encoded SQL is kept under this, splitting the id list as needed
SOURCE = "CCRS (California Highway Patrol), data.ca.gov package 'ccrs', public domain"


class PullError(RuntimeError):
    pass


def margin_ft(study: dict) -> float:
    """Bounding-box margin around the line: covers the influence radius and buffer, independent of small edits."""
    return max(500.0, study["radius_ft"], study["buffer_ft"]) + 150.0


def bbox(line: list[tuple[float, float]], margin: float) -> tuple[float, float, float, float]:
    proj = LocalProjection.around(line)
    xs, ys = zip(*(proj.to_xy(*p) for p in line))
    s, w = proj.to_ll(min(xs) - margin, min(ys) - margin)
    n, e = proj.to_ll(max(xs) + margin, max(ys) + margin)
    return s, w, n, e


PULL_FORMAT = 18    # bump when the cleaning changes what a cached pull holds (2: #75; 3: #80-#83, #94; 4: #113; 5: #111; 6: #121; 7: #52 heavy truck; 8: #52 PCF category; 9: #52 trailers; 10: #52 PCF 2024; 11: #132; 12: #142; 13: #147; 14: #154, #155; 15: #143; 16: #169; 17: #174; 18: #191)


def cache_key(study: dict, net: dict) -> str:
    key = [study["from_year"], study["to_year"], net["line"], net.get("corridor_name"), margin_ft(study),
           PULL_FORMAT]
    gs = sorted(g["name"] for g in net.get("grade_separations") or [])
    if gs:                      # the pull's no-coordinate rules use them (#67); none = same key as before
        key.append(gs)
    names = net.get("corridor_names") or []
    if len(names) > 1:          # extra corridor names/refs widen the no-coordinate search (#53)
        key.append(sorted(names))
    raw = json.dumps(key)
    return hashlib.sha1(raw.encode()).hexdigest()


def _select(cols: dict[str, dict]) -> str:
    return ", ".join(cc.q(f["id"]) for f in cols.values())


def _paged(ckan: Ckan, sql_head: str, order_col: str) -> list[dict]:
    """All rows of a query. `order_col` must order rows totally (id + report version), so pages never skip or
    repeat a row. When the server caps rows below our page size, the page shrinks to the cap and paging goes on."""
    out, offset, page = [], 0, PAGE
    while True:
        batch, truncated = ckan.sql_page(f"{sql_head} ORDER BY {order_col} LIMIT {page} OFFSET {offset}")
        out += batch
        if truncated:
            if not batch:
                raise PullError("data.ca.gov returned a truncated, empty page; the pull was stopped.")
            page = len(batch)
        elif len(batch) < page:
            return out
        offset += len(batch)


def _search_core(k) -> str:
    """The core the SQL prefilter searches for: without a leading direction, which is a superset (COLORADO is inside
    both COLORADO BL and E COLORADO BL; #113, Pasadena pulled 0). Python matching (`same_core`) then decides, as
    before. Short cores are matched as whole words since #121, so "4TH" from East 4th Street no longer finds 14TH or
    24TH, and it finds CHP's E 4TH ST and 4TH ST, which the spelled-out EAST4TH missed (Dorris, #155).
    "Avenue of Flags" searches FLAGS: CHP writes AVENUE OF FLAGS, AVE OF FLAGS (#154)."""
    bare = drop_directional(k).core
    m = re.match(r"^AVENUE OF (?:THE )?(.+)$", bare)
    return m.group(1) if m else bare


def _corridor_cores(net: dict) -> list[str]:
    """Squeezable cores of every corridor name/ref (#53), for the SQL name prefilter."""
    out = []
    for k in grade.corridor_keys(net):
        c = _search_core(k)
        if c not in out:
            out.append(c)
    return out


# Characters left out of street-name matching on both sides: spaces, apostrophes, and the LIKE wildcards % and _
# (an OSM name must never act as a pattern). data.ca.gov refuses LIKE ... ESCAPE (no rights on like_escape, 2026-10-19),
# so the wildcards are removed rather than escaped.
_SQ_DROP = (" ", "'", "%", "_", "-", ".")     # hyphen and dot too: ALVARADO-NILES / ALVARADO NILES (#80)


def _sq_sql(col: str) -> str:
    """UPPER(col) with `_SQ_DROP` characters removed, for name LIKE matching."""
    expr = f"UPPER({col})"
    for ch in _SQ_DROP:
        expr = f"REPLACE({expr}, '{ch * 2 if ch == chr(39) else ch}', '')"
    return expr


def _like_word(w: str) -> str:
    """A street-name word for a LIKE pattern, squeezed the same way as `_sq_sql`."""
    for ch in _SQ_DROP:
        w = w.replace(ch, "")
    return w


def _like(col_sql: str, w: str) -> str:
    return f"{col_sql} LIKE '%{_like_word(w)}%'"


# Short street names are matched as whole words, not inside other text (#121): squeezed, the placeholder NOT STATED
# contains STATE, so every report without a cross street named a "State Street" corridor (Santa Barbara, 6,136 junk
# rows from four counties); MAIN is inside MAINE AV and ROMAINE ST, STATE inside INTERSTATE and ESTATES. Longer names
# stay squeezed: CHP splits words the map writes as one (MC FADDEN AV for McFadden Avenue, 2024: 23 rows), and a
# long core inside other text is rare (CRENSHAW, WILSHIRE, ATLANTIC, EL CAMINO REAL: no false hits, 2024).
SHORT_CORE = 6
_SP_SPACE = ("-", ".", ",", "/", "(", ")", "&", "#", "@", ";", ":")    # read as a word break
_SP_DROP = ("'", "%", "_")                                             # dropped (O'NEIL = ONEIL; never a pattern)


def _sp_sql(col: str) -> str:
    """' ' || UPPER(col) || ' ' with word breaks as single spaces, for whole-word LIKE matching (#121)."""
    expr = f"UPPER({col})"
    for ch in _SP_DROP:
        expr = f"REPLACE({expr}, '{ch * 2 if ch == chr(39) else ch}', '')"
    for ch in _SP_SPACE:
        expr = f"REPLACE({expr}, '{ch}', ' ')"
    for _ in range(2):
        expr = f"REPLACE({expr}, '  ', ' ')"
    return f"(' ' || {expr} || ' ')"


def _spaced(t: str | None) -> str:
    """Python twin of `_sp_sql`: ' WORD WORD '."""
    u = (t or "").upper()
    for ch in _SP_DROP:
        u = u.replace(ch, "")
    return " " + " ".join("".join(ch if ch.isalnum() else " " for ch in u).split()) + " "


def _is_short(w: str) -> bool:
    return len(_like_word(w)) <= SHORT_CORE


def _placeholder(raw: str | None) -> bool:
    """NOT STATED, UNKNOWN, PRIVATE PROPERTY, blank: the field names no street (#94, #121)."""
    return _squeeze(raw) in NO_CROSS


def _name_cond(alias: str, w: str, route: bool) -> str:
    """One road column (alias suffix p or s) names this search word. A short word is matched as a whole word and
    never in a placeholder (NOT STATED, PRIVATE PROPERTY; #121); longer words and route spellings stay squeezed."""
    if route or not _is_short(w):
        return _like(f"sq_{alias}", w)
    words = " OR ".join(f"sp_{alias} LIKE '%{x}%'" for x in _word_forms(w))
    return f"(({words}) AND sp_{alias} NOT IN ({_SP_PLACEHOLDERS}))"


def _word_forms(w: str) -> list[str]:
    """' DEL AMO ' and, run together as CHP also writes it, ' DELAMO ' (Lakewood, DELAMO BL)."""
    sp = _spaced(w)
    glued = f" {_like_word(w)} "
    return [sp] if glued == sp else [sp, glued]


# the spaced form of each placeholder CHP writes (squeezed set: NO_CROSS)
_SP_PLACEHOLDERS = ", ".join(f"'{x}'" for x in (" NOT STATED ", " UNKNOWN ", " UNK ", " N A ", " NONE ", " NO STREET ",
                                                 " PRIVATE PROPERTY "))


def _road_aliases(pr: str, sr: str) -> str:
    """Squeezed (sq_) and whole-word (sp_) forms of both road columns, computed once per row (short URL, #113)."""
    return f"{_sq_sql(pr)} AS sq_p, {_sq_sql(sr)} AS sq_s, {_sp_sql(pr)} AS sp_p, {_sp_sql(sr)} AS sp_s"


# A street-name area must be near the corridor (#132): Santa Maria's Main St & Ray St found Pleasanton, 250 mi away.
# Near = at least PLAUSIBLE_MIN of that area's own GPS crashes within PLAUSIBLE_MI of the corridor box. CCRS gives no
# jurisdiction boundaries; an area's GPS crashes show where it is (its other agencies record GPS even when the
# corridor's own police don't: Alameda County around Union City, #35).
PLAUSIBLE_MI = 5
PLAUSIBLE_MIN = 3


def _areas_near(ckan: Ckan, rid: str, cols: dict, area_col: str, near: tuple) -> dict[str, int]:
    """GPS crashes per area within the widened corridor box (one grouped query)."""
    lat, lon = cc.num_expr(cols["lat"]), cc.num_expr(cols["lon"])
    s, w, n, e = near
    a = cc.q(cols[area_col]["id"])
    rows = ckan.sql(f"SELECT {a} AS area, COUNT(*) AS n FROM {cc.q(rid)} WHERE {lat} BETWEEN {s:.6f} AND {n:.6f} "
                    f"AND {lon} BETWEEN {w:.6f} AND {e:.6f} GROUP BY {a}")
    return {str(r["area"]).strip(): int(r["n"]) for r in rows if r.get("area") not in (None, "")}


def _plausible(areas, near: dict[str, int], why: str, log: dict | None) -> set[str]:
    """The areas with PLAUSIBLE_MIN or more GPS crashes near the corridor; the rest are logged once each (#132)."""
    keep = {x for x in areas if near.get(x, 0) >= PLAUSIBLE_MIN}
    if log is not None:
        seen = {r["area"] for r in log.setdefault("area_rejected", [])}
        log["area_rejected"] += [{"area": x, "found_by": why, "reason": f"{near.get(x, 0)} of its GPS crashes within "
                                  f"{PLAUSIBLE_MI} mi of the corridor (needs {PLAUSIBLE_MIN})"}
                                 for x in sorted(set(areas) - keep) if x not in seen]
    return keep


def _area_by_street_names(ckan: Ckan, rid: str, cols: dict, area_col: str, bad_xy: str, cores: list[str],
                          cross: list[str], near: dict[str, int] | None = None, log: dict | None = None) -> list[str]:
    """Area (county or city code) from reports naming the corridor street AND one of its study cross streets,
    near the corridor (`near`: GPS crashes per area around it, #132). Areas with >= 2 such reports are searched;
    otherwise the single best area."""
    if not cores or not cross:
        return []
    pr, sr = cc.q(cols["primary_road"]["id"]), cc.q(cols["secondary_road"]["id"])

    def like(alias: str, words: list[str]) -> str:
        return " OR ".join(_name_cond(alias, x, route) for w in words for x, route in _search_words(w))

    # Each road column is squeezed ONCE in a subquery, then compared by its short alias: repeating the REPLACE chain
    # for every corridor x cross-street pattern made a 12 KB URL and HTTP 414 (Pasadena, 17 cross streets, #113).
    # A cross-street list still too long for one URL is split and the counts added.
    a = cc.q(cols[area_col]["id"])
    inner = f"SELECT {a} AS area, {_road_aliases(pr, sr)} FROM {cc.q(rid)} WHERE ({bad_xy})"

    def query(xs: list[str]) -> str:
        pair = f"(({like('p', cores)}) AND ({like('s', xs)})) OR (({like('s', cores)}) AND ({like('p', xs)}))"
        return f"SELECT area, COUNT(*) AS n FROM ({inner}) q WHERE {pair} GROUP BY area ORDER BY n DESC LIMIT 20"

    parts = [cross]
    while any(len(urllib.parse.quote(query(x))) > MAX_URL_SQL and len(x) > 1 for x in parts):
        parts = [h for x in parts for h in ((x[:len(x) // 2], x[len(x) // 2:]) if len(x) > 1 else (x,))]
    counts: dict[str, int] = {}
    for x in parts:
        for r in ckan.sql(query(x)):
            if r.get("area") not in (None, ""):
                k = str(r["area"]).strip()
                counts[k] = counts.get(k, 0) + int(r["n"])
    rows = sorted(counts.items(), key=lambda kv: -kv[1])
    if rows and near:                                         # without GPS nearby there is nothing to judge by
        keep = _plausible([x for x, _ in rows], near, "street names", log)
        rows = [(x, n) for x, n in rows if x in keep]
    if not rows:
        return []
    return [x for x, n in rows if n >= 2] or [rows[0][0]]


def _by_ids(ckan: Ckan, rid: str, cols: dict[str, dict], ids: list[str]) -> list[dict]:
    rows = []
    for i in range(0, len(ids), ID_CHUNK):
        chunk = ids[i:i + ID_CHUNK]
        rows += _ids_query(ckan, rid, cols, chunk)
    return rows


def _ids_query(ckan: Ckan, rid: str, cols: dict[str, dict], ids: list[str]) -> list[dict]:
    """Rows for these ids; when the server caps the answer, split the id list until every part fits."""
    idcol = cols["collision_id"]
    numeric = idcol.get("type", "text") in ("int", "int4", "int8", "numeric", "float8", "float")
    lit = ", ".join(str(int(x)) if numeric and str(x).isdigit() else "'" + str(x).replace("'", "''") + "'"
                    for x in ids)               # a text id column compared to bare numbers fails in PostgreSQL
    sql = f"SELECT {_select(cols)} FROM {cc.q(rid)} WHERE {cc.q(idcol['id'])} IN ({lit})"
    if len(ids) > 1 and len(urllib.parse.quote(sql)) > MAX_URL_SQL:       # would be HTTP 414: split first
        mid = len(ids) // 2
        return _ids_query(ckan, rid, cols, ids[:mid]) + _ids_query(ckan, rid, cols, ids[mid:])
    rows, truncated = ckan.sql_page(sql)
    if not truncated:
        return rows
    if len(ids) == 1:
        raise PullError(f"data.ca.gov capped the rows for one crash ({ids[0]}); the pull was stopped.")
    mid = len(ids) // 2
    return _ids_query(ckan, rid, cols, ids[:mid]) + _ids_query(ckan, rid, cols, ids[mid:])


def _squeeze(t: str | None) -> str:
    return "".join(ch for ch in (t or "").upper() if ch.isalnum())


def _names_street(raw: str | None, keys) -> bool:
    """Does a CCRS road field name this street? CHP sometimes writes a full address ("14605 CRENSHAW BLVD.-
    GARDENA- CA 90249"), so fall back to the squeezed core inside the text, as the SQL prefilter does."""
    if _placeholder(raw):
        return False                          # NOT STATED contains STATE (#121)
    k = street_key(raw)
    if k and any(same_core(k, x) for x in keys):
        return True
    routes = {route_number(x) for x in keys} - {None}
    if routes & route_numbers(raw):        # SR-1, RT 1, HWY 1, "PCH - SR1" for a corridor tagged CA 1 (#83)
        return True
    sq, sp = _squeeze(raw), _spaced(raw)
    return any(route_number(x) is None and len(_squeeze(x.core)) >= 4
               and (any(f in sp for f in _word_forms(x.core)) if _is_short(x.core) else _squeeze(x.core) in sq)
               for x in keys)


def _search_words(core: str) -> list[tuple[str, bool]]:
    """(word, is a route spelling) for one corridor core. Route spellings stay squeezed (SR-1 = SR 1 = SR1)."""
    words = _like_words(core)
    return [(w, words != [core]) for w in words]


def _like_words(core: str) -> list[str]:
    """Search words for one corridor core: the core itself, or every way CHP spells a route (SR 1 -> SR1, RT1,
    HWY1, ROUTE1, STATEROUTE1, CA1). Over-matches (RT10) are dropped in code by `_names_street`."""
    m = re.match(r"^(I|US|SR) (\d+)$", core)
    if not m:
        return [core]
    return [p + m.group(2) for p in ROUTE_SPELLINGS[m.group(1)]]


# A no-GPS report filed in a city the corridor never enters can't be on it (#142): Buena Park's Beach Blvd pulled
# ~220 Huntington Beach reports naming Beach Blvd and a study cross street. The corridor's cities come from OSM
# boundaries along the line + buffer (network.corridor_cities). CHP and OSM spell some cities differently (Carmel /
# Carmel-by-the-Sea, Saint Helena / St. Helena, Angels Camp / Angels, La Canada / La Cañada), and CHP files some
# reports under campuses, park districts, airports and harbors that are no OSM city: those are never judged.
_SPECIAL_AREA = re.compile(r"^(UC |CSU |CAL POLY|SAN FRANCISCO STATE|SAN JOSE STATE|SAN DIEGO STATE)|UNIV|PK DIST|"
                           r"PARK DIST|AIRPORT|HARBOR|PORT OF|MEDICAL CENTER", re.I)


def city_key(name: str | None) -> str:
    t = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().upper().strip()
    for p in ("CITY AND COUNTY OF ", "CITY OF ", "TOWN OF "):
        t = t.removeprefix(p)
    t = re.sub(r"\bSAINT\b", "ST", t)
    return re.sub(r"[^A-Z0-9]", "", t)


def _same_city(k: str, a: str) -> bool:
    return k == a or (min(len(k), len(a)) >= 6 and (a.startswith(k) or k.startswith(a)))


@functools.lru_cache(maxsize=1)
def known_cities() -> frozenset[str]:
    """California's incorporated cities (data/reference/ca_cities.csv): CCRS names that OSM also has as cities."""
    from .settings import ROOT
    with (ROOT / "data" / "reference" / "ca_cities.csv").open(newline="") as f:
        return frozenset(city_key(r["ccrs_city_name"]) for r in csv.DictReader(f))


def _city_allowed(city: str | None, allowed: set[str], outside: bool = False) -> bool | None:
    """True / False, or None when the report's city can't be judged (blank, a campus or district). Where the corridor
    runs through unincorporated land, a name that is no incorporated city (Kensington, Broadmoor: unincorporated places
    CHP files under their own name, #147) counts like Unincorporated."""
    if not city or _SPECIAL_AREA.search(city):
        return None
    k = city_key(city)
    if not k:
        return None
    if any(_same_city(k, a) for a in allowed):
        return True
    if outside and not any(_same_city(k, a) for a in known_cities()):
        return True
    return False


# GPS written as degrees-minutes-seconds in a decimal field (#143, user decision 2026-10-21, docs/03): San Jose PD
# writes 37°14'26.77" as 37.142677, so the point lands ~30 km away, outside the corridor box, and the crash is lost.
# Per agency and year, where its GPS clearly carries the DMS digits (minutes and seconds < 60 in both coordinates),
# points written in the DMS image of the corridor box are converted and kept only if they land near the streets the
# report names; otherwise the crash is treated as having no GPS.
# Measured on CCRS 2021-25 (Tester's mirror): most agencies show the digits on 30-40% of their points, a few small
# ones up to 67%; San Jose PD 85-88% in 2021-24 and 55% in 2025. 75% flags San Jose PD 2021-24 and nothing else.
DMS_SHARE = 0.75         # share of an agency-year's GPS points with the DMS digits: clearly DMS
# A mixed agency-year (SJPD 2025: 55%, likely fixed partway through the year), clearly above the 30-40% baseline:
# the same per-point rule (user, 2026-10-21, docs/03). A point that fits the report's streets as written is left
# alone; one that fits converted is converted; one that fits neither is treated as having no GPS.
DMS_SHARE_MIXED = 0.5
DMS_MIN_POINTS = 20      # sample needed to judge an agency-year
DMS_SAMPLE = 1000


def dms_encode(v: float) -> float:
    """The decimal number an agency writes for v when it writes degrees, minutes, seconds as DDD.MMSSss."""
    a = abs(v)
    d = int(a)
    m = int((a - d) * 60 + 1e-9)
    sec = ((a - d) * 60 - m) * 60
    return math.copysign(d + m / 100 + sec / 10000, v)


def dms_decode(v: float) -> float | None:
    """DDD.MMSSss -> decimal degrees; None when the digits can't be minutes and seconds (either >= 60)."""
    a = abs(v)
    d = int(a)
    mm = (a - d) * 100
    m = int(mm + 1e-7)
    sec = (mm - m) * 100
    if m >= 60 or sec >= 60:
        return None
    return math.copysign(d + m / 60 + sec / 3600, v)


def _dms_share(ckan: Ckan, rid: str, cols: dict, agency: str, cache: dict) -> float:
    """Share of an agency's GPS points (a sample) that carry the DMS digits in both coordinates; 0 if too few."""
    key = (rid, agency)
    if key not in cache:
        lat, lon = cc.num_expr(cols["lat"]), cc.num_expr(cols["lon"])
        rows = ckan.sql(f"SELECT {lat} AS la, {lon} AS lo FROM {cc.q(rid)} WHERE {cc.q(cols['ncic']['id'])} = "
                        f"'{agency.replace(chr(39), chr(39) * 2)}' AND {lat} BETWEEN {cc.CA_LAT[0]} AND {cc.CA_LAT[1]} "
                        f"AND {lon} BETWEEN {cc.CA_LON[0]} AND {cc.CA_LON[1]} LIMIT {DMS_SAMPLE}")
        pts = [(float(r["la"]), float(r["lo"])) for r in rows if r.get("la") is not None and r.get("lo") is not None]
        hits = sum(dms_decode(a) is not None and dms_decode(b) is not None for a, b in pts)
        cache[key] = hits / len(pts) if len(pts) >= DMS_MIN_POINTS else 0.0
    return cache[key]


def point_fits_streets(c: dict, net: dict) -> bool:
    """The street check for a point from another source (DMS-converted GPS #143, FARS #174): see `_dms_check`."""
    line = Polyline([tuple(p) for p in net["line"]])
    studies = [i for i in net.get("intersections", []) if i.get("is_study") and i.get("lat") is not None]
    return _dms_check(c, line, studies, grade.corridor_keys(net))


def _dms_check(c: dict, line: Polyline, studies: list[dict], corridor_keys) -> bool:
    """A point is kept only near the streets the report names: within the GPS-check distance (plus the reported
    offset) of the study intersection it names, or of the corridor line when it names the corridor."""
    from .assign import GPS_CHECK_FT, _stated_intersection
    tol = GPS_CHECK_FT + (c.get("offset_ft") or 0.0)
    st = _stated_intersection(c, studies, corridor_keys)
    if st is not None:
        x, y = line.proj.to_xy(c["lat"], c["lon"])
        sx, sy = line.proj.to_xy(st["lat"], st["lon"])
        return math.hypot(x - sx, y - sy) <= tol
    names_corridor = any(_names_street(c.get(f), corridor_keys) for f in ("primary_road", "secondary_road"))
    return names_corridor and line.project(c["lat"], c["lon"]).offset_ft <= tol


def _refile_key(c: dict) -> tuple | None:
    """Same crash filed twice under two Collision Ids (#81): same agency, same report number (when CCRS gives one),
    same date-time and the same two roads. Report numbers alone are not unique (SFPD reuses them), hence the rest."""
    if not c.get("reported_at") or not (c.get("primary_road") or c.get("secondary_road")):
        return None
    return (c.get("agency") or "", c.get("report_number") or "", c["reported_at"],
            _squeeze(c.get("primary_road")), _squeeze(c.get("secondary_road")))


def _same_details(a: dict, b: dict, parties: dict[str, list]) -> bool:
    """Without a report number, agency + minute + roads could be two real crashes at one corner: they must also
    agree on collision type, killed, injured and number of parties (PM review of #87)."""
    return (a.get("collision_type") == b.get("collision_type") and a.get("killed") == b.get("killed")
            and a.get("injured") == b.get("injured")
            and len(parties.get(a["crash_id"], [])) == len(parties.get(b["crash_id"], [])))


def _drop_refiled(crashes: dict[str, dict], parties: dict[str, list], log: dict) -> None:
    """Keep one row per refiled crash: the highest report version, then the lowest Collision Id. Pairs are logged;
    look-alikes without a report number that differ in details are kept and logged as `possible_refile`."""
    groups: dict[tuple, list[str]] = {}
    for cid, c in crashes.items():
        k = _refile_key(c)
        if k is not None:
            groups.setdefault(k, []).append(cid)
    log["same_crash_refiled_dropped"] = 0
    log["same_crash_refiled"] = []
    log["possible_refile"] = []
    for key, ids in groups.items():
        if len(ids) < 2:
            continue
        keep = max(ids, key=lambda i: (crashes[i]["report_version"], -int(i) if i.isdigit() else 0))
        drop = [i for i in ids if i != keep]
        if not key[1]:                       # no report number: details must agree too
            differ = [i for i in drop if not _same_details(crashes[keep], crashes[i], parties)]
            if differ:
                log["possible_refile"].append(sorted([keep, *differ]))
            drop = [i for i in drop if i not in differ]
        if not drop:
            continue
        log["same_crash_refiled"].append({"kept": keep, "dropped": sorted(drop)})
        log["same_crash_refiled_dropped"] += len(drop)
        for i in drop:
            del crashes[i]


NO_CROSS = {"", "NOTSTATED", "UNKNOWN", "UNK", "NA", "NONE", "NOSTREET", "PRIVATEPROPERTY"}


def _no_cross_street(roads: list, on_idx: list[int]) -> bool:
    """The road fields other than the corridor give no cross street: blank, a placeholder, or 1-2 letters of junk."""
    others = [roads[i] for i in range(len(roads)) if i not in on_idx]
    if not others and len(on_idx) == len(roads):
        return False                    # both fields name the corridor: nothing missing
    return all(_squeeze(rd) in NO_CROSS or len(_squeeze(rd)) <= 2 for rd in others)


def pull(study: dict, net: dict, ckan: Ckan, progress=None) -> dict:
    """`progress(step, done, total)`, when given, is told what the pull is doing (#54, background pulls)."""
    tell = progress or (lambda step, done, total: None)
    if not net.get("line"):
        raise PullError("Draw the corridor first.")
    years = list(range(study["from_year"], study["to_year"] + 1))
    res = cc.table_resources(ckan.get("package_show", id=cc.PACKAGE))
    log = {"rows_read": 0, "outside_window_dropped": 0, "deleted_dropped": 0, "duplicate_versions_dropped": 0,
           "no_coords_read": 0, "no_coords_other_city": 0, "no_coords_not_corridor_street": 0, "no_coords_off_study_stretch": 0,
           "no_coords_grade_separated": 0, "gps_beyond_margin_dropped": 0,
           "implausible_coords": 0, "bad_dates_dropped": 0, "duplicate_parties_dropped": 0, "version_ties_first_kept": 0, "preliminary_kept": 0,
           "feet_typed_as_miles_fixed": 0, "years_missing": [], "parties_missing_years": [], "iwp_missing_years": [],
           "missing_fields": {}, "unknown_injury_values": [], "cities": [], "area_rejected": [],
           "gps_dms_corrected": 0, "gps_dms_unconfirmed": 0, "gps_dms_agencies": []}
    margin = margin_ft(study)
    line = Polyline([tuple(p) for p in net["line"]])
    s, w, n, e = bbox(net["line"], margin)
    near = bbox(net["line"], margin + PLAUSIBLE_MI * 5280)     # where a street-name area must have crashes (#132)
    cores = _corridor_cores(net)
    corridor_keys = grade.corridor_keys(net)
    # One corner can carry two cross-street names ("Eastin Drive / Lowry Road"): each one counts (Lowry Rd, Union City).
    cross_keys = [k for k in (street_key(part) for i in net.get("intersections", []) if i.get("is_study")
                              for part in str(i.get("name") or "").split("/")) if k]
    cross_cores = [c for c in dict.fromkeys(_search_core(k) for k in cross_keys) if c not in cores and len(c) >= 3]
    gs_keys = grade.crossing_keys(net)      # roads crossing over/under the corridor (N7, #67)
    name_area: list[str] | None = None     # found once from street names, reused for every year
    near_n: dict[str, int] | None = None   # GPS crashes per area near the corridor, read once (#132)
    corridor_cities = net.get("cities")      # OSM cities along the line (#142); None = not known, nothing dropped
    studies = [i for i in net.get("intersections", []) if i.get("is_study") and i.get("lat") is not None]
    dms_cache: dict = {}                     # (table, agency) -> share of GPS points with DMS digits (#143)
    dms_ids: dict[str, set] = {"corrected": set(), "unconfirmed": set()}
    gps_cities: Counter = Counter()
    other_city: Counter = Counter()
    log["area_source"] = None
    raw_by_year: dict[int, list[dict]] = {}

    for yi, y in enumerate(years):
        tell(f"Crash reports {y}", yi, len(years))
        rid = res["crashes"].get(y)
        if not rid:
            log["years_missing"].append(y)
            continue
        cols, missing = cc.resolve_columns(ckan.fields(rid), cc.CRASH_COLS)
        req = [m for m in missing if m in cc.CRASH_REQUIRED]
        if req:
            raise PullError(f"CCRS {y} is missing required columns: {', '.join(req)}. The data layout changed; "
                            "update the CCRS adapter.")
        if missing:
            log["missing_fields"][f"crashes_{y}"] = missing
        lat, lon, cid = cc.num_expr(cols["lat"]), cc.num_expr(cols["lon"]), cc.q(cols["collision_id"]["id"])
        if "report_version" in cols:
            cid += ", " + cc.q(cols["report_version"]["id"])
        head = f"SELECT {_select(cols)} FROM {cc.q(rid)}"
        box = f"({lat} BETWEEN {s:.6f} AND {n:.6f} AND {lon} BETWEEN {w:.6f} AND {e:.6f})"
        # and the box's image in degrees-minutes-seconds (#143), in the same query
        es, en = dms_encode(s), dms_encode(n)
        ew, ee = sorted((dms_encode(w), dms_encode(e)))
        dms_box = f"({lat} BETWEEN {es:.6f} AND {en:.6f} AND {lon} BETWEEN {ew:.6f} AND {ee:.6f})"
        rows = _paged(ckan, f"{head} WHERE {box} OR {dms_box}", cid)
        la_id, lo_id = cols["lat"]["id"], cols["lon"]["id"]

        def in_box(r):
            a, b = cc._num(r.get(la_id)), cc._num(r.get(lo_id))
            return a is not None and b is not None and s <= a <= n and w <= b <= e
        with_xy = [r for r in rows if in_box(r)]
        dms_rows = [r for r in rows if not in_box(r)]
        recs = []
        for r in with_xy:
            c = cc.crash_record(r, cols)
            # The box is a rectangle; on a diagonal corridor most of it is far from the line. Rows beyond the
            # margin can't be in the study at any radius/buffer the margin allows, so they stop here (#54).
            if c["lat"] is not None and c["lon"] is not None and line.project(c["lat"], c["lon"]).offset_ft > margin:
                log["gps_beyond_margin_dropped"] += 1
                continue
            recs.append((c, "gps"))
        # GPS written as degrees-minutes-seconds (#143): read the DMS image of the corridor box
        dms_no_gps = []
        if "ncic" in cols:
            for r in dms_rows:
                agency = str(r.get(cols["ncic"]["id"]) or "").strip()
                share = _dms_share(ckan, rid, cols, agency, dms_cache) if agency else 0.0
                if share < DMS_SHARE_MIXED:
                    continue
                clear = share >= DMS_SHARE
                c = cc.crash_record(r, cols)
                la, lo = (dms_decode(c["lat"]), dms_decode(c["lon"])) if c["lat"] is not None else (None, None)
                if la is None or lo is None:
                    continue
                written_fits = _dms_check(c, line, studies, corridor_keys)
                c.update(lat=la, lon=lo, gps_as_written=[r.get(la_id), r.get(lo_id)])
                if line.project(la, lo).offset_ft > margin:
                    continue                  # converted, it's somewhere else along the box: not this corridor
                if written_fits:              # fits its streets as written (mixed years): left alone
                    continue
                if _dms_check(c, line, studies, corridor_keys):
                    recs.append((c, "gps_dms_corrected"))
                    dms_ids["corrected"].add(c["crash_id"])
                else:                         # fits neither as written nor converted: treated as having no GPS,
                    dms_no_gps.append({**r, la_id: None, lo_id: None})      # never left ~30 km away (PM review 2)
                    dms_ids["unconfirmed"].add(c["crash_id"])
                log["gps_dms_agencies"] = sorted(set(log["gps_dms_agencies"])
                                                 | {f"{agency} ({y}{'' if clear else ', mixed'})"})
        log["cities"] = sorted(set(log["cities"]) | {r["city"] for r, _ in recs if r["city"]})
        # Crashes with no usable coordinates: same county (or city) as the GPS crashes, on the corridor street by
        # name; then, in code, only those whose cross street is one of the study intersections (the study stretch).
        area_col = "county_code" if "county_code" in cols else "city_code" if "city_code" in cols else None
        # Only GPS crashes whose report names the corridor say where the corridor is: a Woodland PD crash
        # (ELM ST & COURT ST, county 57) with GPS in Marina must not send the search to Yolo County (#111).
        gps_area = {str(r[area_col]) for r, _ in recs if area_col and r.get(area_col)
                    and any(_names_street(r.get(f), corridor_keys) for f in ("primary_road", "secondary_road"))}
        # Where each area's own crashes are (once per pull): a stray GPS point (a Pleasanton report placed in Santa
        # Maria) or a shared street pair must not send the search 250 mi away (#132).
        if area_col and near_n is None:
            near_n = _areas_near(ckan, rid, cols, area_col, near)
            if not any(n >= PLAUSIBLE_MIN for n in near_n.values()):
                log["area_unchecked"] = (f"no area has {PLAUSIBLE_MIN} GPS crashes within {PLAUSIBLE_MI} mi of the "
                                         "corridor, so the search areas were not checked")
                near_n = {}
        if near_n:
            gps_area = _plausible(gps_area, near_n, "GPS crash in the corridor box", log)
        bad_xy = (f"{lat} IS NULL OR {lon} IS NULL OR {lat} NOT BETWEEN {cc.CA_LAT[0]} AND {cc.CA_LAT[1]} "
                  f"OR {lon} NOT BETWEEN {cc.CA_LON[0]} AND {cc.CA_LON[1]}")
        # The area found from the reports' own street names (corridor street + a study cross street) is always
        # searched too, found once per pull (tried again each year until a year has such reports): GPS alone can
        # point at the wrong county (#111; Union City has no GPS, #35).
        if cores and area_col and not name_area:
            name_area = _area_by_street_names(ckan, rid, cols, area_col, bad_xy, cores, cross_cores, near_n, log)
        area = sorted(gps_area | set(name_area or []))
        if gps_area:
            log["area_source"] = log["area_source"] or "GPS crashes in the corridor box"
        elif area:
            log["area_source"] = log["area_source"] or "street names (no GPS crash in the corridor box)"
        no_xy = []
        if cores and area:
            pr, sr = cc.q(cols["primary_road"]["id"]), cc.q(cols["secondary_road"]["id"])
            # squeezed once per row in a subquery, compared by alias (short URL, #113)
            names = " OR ".join(_name_cond(a, w, route) for core in cores for w, route in _search_words(core)
                                for a in ("p", "s"))
            area_in = ", ".join("'" + c.replace("'", "''") + "'" for c in area)
            inner = (f"SELECT {_select(cols)}, {_road_aliases(pr, sr)} FROM {cc.q(rid)} "
                     f"WHERE ({bad_xy}) AND {cc.q(cols[area_col]['id'])} IN ({area_in})")
            no_xy = _paged(ckan, f"SELECT * FROM ({inner}) q WHERE ({names})", cid)
        if dms_no_gps:
            ids = {str(r[cols["collision_id"]["id"]]) for r in no_xy}
            no_xy = list(no_xy) + [r for r in dms_no_gps if str(r[cols["collision_id"]["id"]]) not in ids]
        log["no_coords_read"] += len(no_xy)
        # cities a no-GPS report may come from (#142): those the line enters, unincorporated county where it leaves
        # city limits, and any city with 2+ of its GPS crashes along the corridor (an OSM boundary can be missing)
        gps_cities.update(r["city"] for r, _ in recs if r.get("city"))
        allowed = None
        if corridor_cities is not None:
            allowed = {city_key(x) for x in corridor_cities["cities"]}
            allowed |= {city_key(x) for x, n in gps_cities.items() if n >= 2}
            if corridor_cities["outside"]:
                allowed |= {"UNINCORPORATED"} | {city_key(x) for x in corridor_cities["counties"]}
        for r in no_xy:
            c = cc.crash_record(r, cols)
            if allowed is not None and _city_allowed(c.get("city"), allowed, corridor_cities["outside"]) is False:
                log["no_coords_other_city"] += 1
                other_city[c["city"]] += 1
                continue
            log["implausible_coords"] += c["bad_coords"]
            roads = [c["primary_road"], c["secondary_road"]]
            on_idx = [i for i, rd in enumerate(roads) if _names_street(rd, corridor_keys)]
            on = [roads[i] for i in on_idx]
            other = [street_key(rd) for i, rd in enumerate(roads) if i not in on_idx and street_key(rd)]
            if not on:
                log["no_coords_not_corridor_street"] += 1
            elif grade.on_crossing_road(c, corridor_keys, gs_keys):
                # On a road passing over or under the corridor: never meets it (N7, #67). Kept and listed.
                log["no_coords_grade_separated"] += 1
                c["exclude_rule"] = "grade_separated_crossing"
                recs.append((c, "unmatched"))
            elif _no_cross_street(roads, on_idx):
                # The report gives no usable cross street ('NOT STATED', blank, 'PRIVATE PROPERTY', junk): where on
                # the corridor it happened is unknown. Not a side street (#82): its own rule and count.
                rule = "private_property" if any("PRIVATEPROPERTY" in _squeeze(rd) for rd in roads if rd) \
                    else "no_cross_street"
                log[f"no_coords_{rule}"] = log.get(f"no_coords_{rule}", 0) + 1
                if rule == "private_property":
                    c["exclude_rule"] = rule        # not on the corridor
                else:
                    c["review_reason"] = rule       # user, 2026-10-19 (#94): on the corridor, place unknown -> review
                recs.append((c, "unmatched"))
            else:
                at_crossing = any(grade.same_road(k, x) for k in other for x in gs_keys)   # corridor, by an overpass
                if cross_keys and not at_crossing and not any(same_core(k, x) for k in other for x in cross_keys):
                    # Side street, not one of the corridor's own intersections: excluded, but kept, counted and
                    # listed under its rule (#39, docs/03).
                    log["no_coords_off_study_stretch"] += 1
                    c["exclude_rule"] = "cross_street_not_on_corridor"
                recs.append((c, "unmatched"))
        log["rows_read"] += len(with_xy) + len(no_xy)
        raw_by_year[y] = recs

    # cleaning: window, CHP-deleted, duplicate report versions (keep the highest), preliminary flagged
    crashes: dict[str, dict] = {}
    dup_seen = 0
    for y, recs in raw_by_year.items():
        for c, loc in recs:
            if c["year"] is None:
                log["bad_dates_dropped"] += 1
                continue
            if c["year"] not in years:
                log["outside_window_dropped"] += 1
                continue
            c["location_source"] = loc
            prev = crashes.get(c["crash_id"])
            if prev is not None:
                dup_seen += 1
                if c["report_version"] == prev["report_version"]:
                    log["version_ties_first_kept"] += 1     # same version twice: keep the first row read
                if c["report_version"] <= prev["report_version"]:
                    continue
            crashes[c["crash_id"]] = c       # the newest version wins, even when it is the deleted one (#53)
    for cid in [k for k, c in crashes.items() if c["deleted"]]:
        log["deleted_dropped"] += 1          # newest version deleted: the crash is gone, older versions don't survive
        del crashes[cid]
    log["duplicate_versions_dropped"] = dup_seen
    if len(log["years_missing"]) == len(years):
        raise PullError("data.ca.gov has no CCRS crash table for any year in the study window. The dataset may have "
                        "been renamed; update the CCRS adapter.")
    if log["bad_dates_dropped"] > max(5, 0.02 * max(1, log["rows_read"])):
        raise PullError(f"{log['bad_dates_dropped']} of {log['rows_read']} crash records have a Crash Date Time in a "
                        "format CrashIQ doesn't recognize. The data layout changed; update the CCRS adapter.")

    # Parties + IWP, per year
    by_year: dict[int, list[str]] = {}
    for c in crashes.values():
        if not c.get("exclude_rule"):   # excluded reports are listed, but never counted: no party/injury lookups (#54)
            by_year.setdefault(c["year"], []).append(c["crash_id"])
    parties: dict[str, list[dict]] = {}
    extents: dict[str, list[str]] = {}
    for yi, (y, ids) in enumerate(sorted(by_year.items())):
        tell(f"Parties and injuries {y}", yi, len(by_year))
        prid, irid = res["parties"].get(y), res["iwp"].get(y)
        if prid:
            pcols, pmiss = cc.resolve_columns(ckan.fields(prid), cc.PARTY_COLS)
            if "collision_id" in pmiss:
                raise PullError(f"CCRS Parties {y} has no Collision Id column.")
            if pmiss:
                log["missing_fields"][f"parties_{y}"] = pmiss
            seen_party = set()
            for r in _by_ids(ckan, prid, pcols, ids):
                pr_ = cc.party_record(r, pcols)
                cid_ = str(r[pcols["collision_id"]["id"]])
                if pr_["party_number"] is not None:       # one row per party, even when versions repeat it
                    if (cid_, pr_["party_number"]) in seen_party:
                        log["duplicate_parties_dropped"] += 1
                        continue
                    seen_party.add((cid_, pr_["party_number"]))
                parties.setdefault(cid_, []).append(pr_)
        else:
            log["parties_missing_years"].append(y)
        if irid:
            icols, imiss = cc.resolve_columns(ckan.fields(irid), cc.IWP_COLS)
            if "collision_id" in imiss or "extent" in imiss:
                raise PullError(f"CCRS InjuredWitnessPassengers {y} lacks Collision Id or ExtentOfInjury.")
            for r in _by_ids(ckan, irid, icols, ids):
                if "witness_only" in icols and cc._truthy(r.get(icols["witness_only"]["id"])):
                    continue
                extents.setdefault(str(r[icols["collision_id"]["id"]]), []).append(r.get(icols["extent"]["id"]))
        else:
            log["iwp_missing_years"].append(y)

    _drop_refiled(crashes, parties, log)   # after the party lookup: party count is one of the checks (#81)
    unknown = set()
    out = []
    for c in sorted(crashes.values(), key=lambda c: (c["date"], c["crash_id"])):
        if c.get("exclude_rule"):
            c.update(severity=None, parties=[], ped=False, bike=False, ebike=False, escooter=False, motorcycle=False, heavy_truck=False,
                     details="not_looked_up")
        else:
            ps = parties.get(c["crash_id"], [])
            sev, unk = cc.severity(c, extents.get(c["crash_id"]))
            unknown.update(unk)
            c.update(severity=sev, parties=ps, **cc.mode_flags(c, ps))
        log["preliminary_kept"] += c["preliminary"]
        log["feet_typed_as_miles_fixed"] += c.pop("offset_fixed")
        out.append(c)
    log["unknown_injury_values"] = sorted(unknown)
    log["gps_dms_corrected"] = len(dms_ids["corrected"] & set(crashes))          # crashes, not report versions (#143)
    log["gps_dms_unconfirmed"] = len(dms_ids["unconfirmed"] - dms_ids["corrected"])
    log["other_cities"] = dict(other_city.most_common())        # no-GPS reports filed in cities off the corridor (#142)
    log["corridor_cities"] = corridor_cities                     # None: OSM couldn't say, so nothing was dropped
    log["kept"] = len(out)
    if not out:  # never a silent empty study
        log["warning"] = ("No crashes found. " + (
            "No area could be identified for this corridor: no GPS crash in the corridor box, and no report names "
            "the corridor street with one of its study cross streets." if not log["area_source"]
            else "Reports from this area exist, but none name this street on the study stretch."))
    log["with_coords"] = sum(c["location_source"] in ("gps", "gps_dms_corrected") for c in out)
    log["without_coords"] = sum(c["location_source"] == "unmatched" for c in out)
    log["excluded_listed"] = sum(bool(c.get("exclude_rule")) for c in out)
    return {"crashes": out, "cleaning": log, "source": SOURCE, "years": years,
            "pulled_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# -- cache + API -------------------------------------------------------------------------------------
def get_cached(db: Database, sid: str) -> dict | None:
    r = db.one("SELECT * FROM crash_pull WHERE study_id = ?", (sid,))
    return {**json.loads(r["payload"]), "cache_key": r["cache_key"]} if r else None


RECENT_TTL_DAYS = 30   # a pull whose window reaches last year or this year is redone after this (CHP keeps revising
                       # preliminary reports, #54); older windows are final and never expire


MISSING_TTL_DAYS = 1     # a pull missing a year's Parties / IWP / Crashes table is refreshed daily until CHP publishes it


def stale(cached: dict, study: dict, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if study["to_year"] < now.year - 1:
        return False
    try:
        pulled = datetime.fromisoformat(cached["pulled_at"])
    except (KeyError, TypeError, ValueError):
        return True
    if pulled.tzinfo is None:
        pulled = pulled.replace(tzinfo=timezone.utc)
    cl = cached.get("cleaning") or {}
    if cl.get("parties_missing_years") or cl.get("iwp_missing_years") or cl.get("years_missing"):
        return (now - pulled).days >= MISSING_TTL_DAYS       # CHP publishes late: look again daily (#188)
    return (now - pulled).days >= RECENT_TTL_DAYS


_STUDY_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def study_lock(sid: str) -> threading.Lock:
    """One pull at a time per study, whether it runs in a request or in the background (#54)."""
    with _LOCKS_GUARD:
        return _STUDY_LOCKS.setdefault(sid, threading.Lock())


def fresh(db: Database, sid: str) -> dict | None:
    """The cached pull when it still matches the study (same key, not expired), else None."""
    study = study_mod.require(db, sid)
    net = network_mod.network(db, sid)
    key = cache_key(study, net) if net.get("line") else None
    cached = get_cached(db, sid)
    return cached if cached and cached["cache_key"] == key and not stale(cached, study) else None


def ensure(db: Database, sid: str, ckan: Ckan, refresh: bool = False, progress=None,
           overpass=None) -> tuple[dict, bool]:
    """(pull result, from_cache). Re-pulls when refreshed or when window/corridor changed. The result is stored
    only if the study still has the same key when the pull ends (compare-and-set); if the corridor or window was
    edited meanwhile, it pulls once more for the new study."""
    with study_lock(sid):
        if not refresh:
            hit = fresh(db, sid)
            if hit:
                return hit, True
        for _ in range(2):
            study = study_mod.require(db, sid)
            net = network_mod.network(db, sid)
            key = cache_key(study, net) if net.get("line") else None
            if net.get("line"):                    # the cities the line enters (#142); cached with the OSM answers
                net = {**net, "cities": network_mod.corridor_cities(db, net["line"], study["buffer_ft"], overpass)}
            result = pull(study, net, ckan, progress)
            from .placement import place_unmatched   # C4: place crashes without coordinates (locator, PR #16)
            place_unmatched(db, net, result, overpass=overpass)
            now = study_mod.require(db, sid)
            now_net = network_mod.network(db, sid)
            if (cache_key(now, now_net) if now_net.get("line") else None) == key:
                db.execute("INSERT OR REPLACE INTO crash_pull (study_id, cache_key, pulled_at, payload) "
                           "VALUES (?,?,?,?)", (sid, key, result["pulled_at"], json.dumps(result)))
                from .assign import forget       # a re-pull in the same second keeps the same pulled_at (#97)
                forget(sid)
                return {**result, "cache_key": key}, False
        raise PullError("The study kept changing while its crashes were being pulled. Try again.")


def ckan_for(request: Request) -> Ckan:
    st = request.app.state
    return Ckan(getattr(st, "ckan", None), retries=getattr(st, "ckan_retries", 3))


router = APIRouter()


def summary(result: dict, from_cache: bool) -> dict:
    return {"count": len(result["crashes"]), "cleaning": result["cleaning"], "source": result["source"],
            "years": result["years"], "pulled_at": result["pulled_at"], "from_cache": from_cache}


_JOBS: dict[str, dict] = {}       # study id -> background pull status (one per study, #54)


def _error_status(e: Exception) -> tuple[int, str]:
    if isinstance(e, (CkanError, network_mod.NetworkError)):
        return 502, str(e)
    if isinstance(e, PullError):
        return 409, str(e)
    return 500, f"The crash pull failed: {e}"


def _run_job(db: Database, sid: str, ckan: Ckan, refresh: bool, job: dict, overpass=None) -> None:
    def progress(step, done, total):
        job.update(step=step, done=done, total=total)
    try:
        result, hit = ensure(db, sid, ckan, refresh, progress, overpass)
        job.update(state="done", step="Done", summary=summary(result, hit))
    except Exception as e:  # noqa: BLE001 - reported to the screen through the status endpoint
        code, msg = _error_status(e)
        job.update(state="error", status=code, error=msg)


@router.post("/studies/{sid}/crashes/pull")
def post_pull(sid: str, request: Request, response: Response, refresh: bool = False, background: bool = False) -> dict:
    db = request.app.state.db
    if background:
        # A cache hit answers at once; otherwise the pull runs in a thread and the screen polls its progress, so a
        # 1-minute pull (10 years, ~40 data.ca.gov calls) is never one frozen request (#54).
        if not refresh:
            hit = fresh(db, sid)
            if hit:
                return summary(hit, True)
        with _LOCKS_GUARD:
            job = _JOBS.get(sid)
            if not job or job["state"] != "running":
                job = {"state": "running", "step": "Starting", "done": 0, "total": 0,
                       "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                _JOBS[sid] = job
                threading.Thread(target=_run_job, args=(db, sid, ckan_for(request), refresh, job,
                                                         getattr(request.app.state, "overpass", None)), daemon=True).start()
        response.status_code = 202
        return {"job": dict(job)}
    try:
        result, hit = ensure(db, sid, ckan_for(request), refresh, overpass=getattr(request.app.state, "overpass", None))
    except (CkanError, PullError, network_mod.NetworkError) as e:
        code, msg = _error_status(e)
        raise HTTPException(code, msg) from e
    return summary(result, hit)


@router.get("/studies/{sid}/crashes/pull/status")
def pull_status(sid: str, request: Request) -> dict:
    study_mod.require(request.app.state.db, sid)
    return dict(_JOBS.get(sid) or {"state": "idle"})


@router.get("/studies/{sid}/crashes")
def get_crashes(sid: str, request: Request, full: bool = False) -> dict:
    """The pulled crashes. Each crash's party list is most of the payload and the screens never read it, so it's
    left out unless `full=true` (#54); exports and findings read the pull directly."""
    db = request.app.state.db
    study_mod.require(db, sid)
    cached = get_cached(db, sid)
    if not cached:
        raise HTTPException(404, "No crashes pulled yet for this study.")
    rows = cached["crashes"] if full else [{k: v for k, v in c.items() if k != "parties"} for c in cached["crashes"]]
    return {**summary(cached, True), "crashes": rows}
