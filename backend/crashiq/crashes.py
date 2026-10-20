"""C3 crash pull: every CCRS crash a corridor study needs, cleaned with logged steps, cached per study.

For each year in the study window (resources resolved at runtime from the CKAN `ccrs` package):
  (a) crashes WITH coordinates inside the corridor's bounding box (+ margin);
  (b) crashes WITHOUT coordinates in the same cities whose PrimaryRoad or SecondaryRoad normalizes to the
      corridor street (they are placed later, C4; until then #10 counts them as `unmatched`);
then Parties and InjuredWitnessPassengers joined by Collision Id. Cleaning steps are counted, never silent.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from . import grade
from . import network as network_mod
from . import study as study_mod
from .db import Database
from .geo import LocalProjection
from .names import same_core, street_key
from .sources import ca_ccrs as cc
from .sources.ckan import Ckan, CkanError

PAGE = 5000
ID_CHUNK = 150          # Collision Ids per Parties/IWP query (URL length)
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


PULL_FORMAT = 2     # bump when the cleaning changes what a cached pull holds (2: live injury codes, #75)


def cache_key(study: dict, net: dict) -> str:
    key = [study["from_year"], study["to_year"], net["line"], net.get("corridor_name"), margin_ft(study),
           PULL_FORMAT]
    gs = sorted(g["name"] for g in net.get("grade_separations") or [])
    if gs:                      # the pull's no-coordinate rules use them (#67); none = same key as before
        key.append(gs)
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


def _corridor_cores(net: dict) -> list[str]:
    k = street_key(net.get("corridor_name"))
    return [k.core] if k else []


# Characters left out of street-name matching on both sides: spaces, apostrophes, and the LIKE wildcards % and _
# (an OSM name must never act as a pattern). data.ca.gov refuses LIKE ... ESCAPE (no rights on like_escape, 2026-10-19),
# so the wildcards are removed rather than escaped.
_SQ_DROP = (" ", "'", "%", "_")


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


def _area_by_street_names(ckan: Ckan, rid: str, cols: dict, area_col: str, bad_xy: str, cores: list[str],
                          cross: list[str]) -> list[str]:
    """Area (county or city code) from reports naming the corridor street AND one of its study cross streets.
    Areas with >= 2 such reports are searched; otherwise the single best area."""
    if not cores or not cross:
        return []
    pr, sr = cc.q(cols["primary_road"]["id"]), cc.q(cols["secondary_road"]["id"])

    def like(col: str, words: list[str]) -> str:
        return " OR ".join(_like(_sq_sql(col), w) for w in words)

    pair = f"(({like(pr, cores)}) AND ({like(sr, cross)})) OR (({like(sr, cores)}) AND ({like(pr, cross)}))"
    a = cc.q(cols[area_col]["id"])
    rows = ckan.sql(f"SELECT {a} AS area, COUNT(*) AS n FROM {cc.q(rid)} WHERE ({bad_xy}) AND ({pair}) "
                    f"GROUP BY {a} ORDER BY n DESC LIMIT 20")
    rows = [(str(r["area"]).strip(), int(r["n"])) for r in rows if r.get("area") not in (None, "")]
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
    rows, truncated = ckan.sql_page(f"SELECT {_select(cols)} FROM {cc.q(rid)} WHERE {cc.q(idcol['id'])} IN ({lit})")
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
    k = street_key(raw)
    if k and any(same_core(k, x) for x in keys):
        return True
    sq = _squeeze(raw)
    return any(len(_squeeze(x.core)) >= 4 and _squeeze(x.core) in sq for x in keys)


def pull(study: dict, net: dict, ckan: Ckan) -> dict:
    if not net.get("line"):
        raise PullError("Draw the corridor first.")
    years = list(range(study["from_year"], study["to_year"] + 1))
    res = cc.table_resources(ckan.get("package_show", id=cc.PACKAGE))
    log = {"rows_read": 0, "outside_window_dropped": 0, "deleted_dropped": 0, "duplicate_versions_dropped": 0,
           "no_coords_read": 0, "no_coords_not_corridor_street": 0, "no_coords_off_study_stretch": 0,
           "no_coords_grade_separated": 0,
           "implausible_coords": 0, "bad_dates_dropped": 0, "duplicate_parties_dropped": 0, "preliminary_kept": 0,
           "feet_typed_as_miles_fixed": 0, "years_missing": [], "parties_missing_years": [], "iwp_missing_years": [],
           "missing_fields": {}, "unknown_injury_values": [], "cities": []}
    s, w, n, e = bbox(net["line"], margin_ft(study))
    cores = _corridor_cores(net)
    corridor_keys = [k for k in [street_key(net.get("corridor_name"))] if k]
    # One corner can carry two cross-street names ("Eastin Drive / Lowry Road"): each one counts (Lowry Rd, Union City).
    cross_keys = [k for k in (street_key(part) for i in net.get("intersections", []) if i.get("is_study")
                              for part in str(i.get("name") or "").split("/")) if k]
    cross_cores = [k.core for k in cross_keys if k.core not in cores and len(k.core) >= 3]
    gs_keys = grade.crossing_keys(net)      # roads crossing over/under the corridor (N7, #67)
    name_area: list[str] | None = None     # found once from street names, reused for every year
    log["area_source"] = None
    raw_by_year: dict[int, list[dict]] = {}

    for y in years:
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
        with_xy = _paged(ckan, f"{head} WHERE {lat} BETWEEN {s:.6f} AND {n:.6f} AND {lon} BETWEEN {w:.6f} AND {e:.6f}", cid)
        recs = [(cc.crash_record(r, cols), "gps") for r in with_xy]
        log["cities"] = sorted(set(log["cities"]) | {r["city"] for r, _ in recs if r["city"]})
        # Crashes with no usable coordinates: same county (or city) as the GPS crashes, on the corridor street by
        # name; then, in code, only those whose cross street is one of the study intersections (the study stretch).
        area_col = "county_code" if "county_code" in cols else "city_code" if "city_code" in cols else None
        area = sorted({str(r[area_col]) for r, _ in recs if area_col and r.get(area_col)})
        bad_xy = (f"{lat} IS NULL OR {lon} IS NULL OR {lat} NOT BETWEEN {cc.CA_LAT[0]} AND {cc.CA_LAT[1]} "
                  f"OR {lon} NOT BETWEEN {cc.CA_LON[0]} AND {cc.CA_LON[1]}")
        if area:
            log["area_source"] = log["area_source"] or "GPS crashes in the corridor box"
        elif cores and area_col:
            # No GPS crash in the box (Union City PD records GPS on 0% of reports, 2026-10-18): find the area from
            # the reports themselves.
            if not name_area:
                name_area = _area_by_street_names(ckan, rid, cols, area_col, bad_xy, cores, cross_cores)
            area = name_area
            if area:
                log["area_source"] = "street names (no GPS crash in the corridor box)"
        no_xy = []
        if cores and area:
            pr, sr = cc.q(cols["primary_road"]["id"]), cc.q(cols["secondary_road"]["id"])
            names = " OR ".join(_like(_sq_sql(c), core) for core in cores for c in (pr, sr))
            area_in = ", ".join("'" + c.replace("'", "''") + "'" for c in area)
            no_xy = _paged(ckan, f"{head} WHERE ({bad_xy}) AND {cc.q(cols[area_col]['id'])} IN ({area_in}) "
                                 f"AND ({names})", cid)
        log["no_coords_read"] += len(no_xy)
        for r in no_xy:
            c = cc.crash_record(r, cols)
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
            if c["deleted"]:
                log["deleted_dropped"] += 1
                continue
            c["location_source"] = loc
            prev = crashes.get(c["crash_id"])
            if prev is not None:
                dup_seen += 1
                if c["report_version"] <= prev["report_version"]:
                    continue
            crashes[c["crash_id"]] = c
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
        by_year.setdefault(c["year"], []).append(c["crash_id"])
    parties: dict[str, list[dict]] = {}
    extents: dict[str, list[str]] = {}
    for y, ids in sorted(by_year.items()):
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

    unknown = set()
    out = []
    for c in sorted(crashes.values(), key=lambda c: (c["date"], c["crash_id"])):
        ps = parties.get(c["crash_id"], [])
        sev, unk = cc.severity(c, extents.get(c["crash_id"]))
        unknown.update(unk)
        c.update(severity=sev, parties=ps, **cc.mode_flags(c, ps))
        log["preliminary_kept"] += c["preliminary"]
        log["feet_typed_as_miles_fixed"] += c.pop("offset_fixed")
        out.append(c)
    log["unknown_injury_values"] = sorted(unknown)
    log["kept"] = len(out)
    if not out:  # never a silent empty study
        log["warning"] = ("No crashes found. " + (
            "No area could be identified for this corridor: no GPS crash in the corridor box, and no report names "
            "the corridor street with one of its study cross streets." if not log["area_source"]
            else "Reports from this area exist, but none name this street on the study stretch."))
    log["with_coords"] = sum(c["location_source"] == "gps" for c in out)
    log["without_coords"] = sum(c["location_source"] == "unmatched" for c in out)
    log["excluded_listed"] = sum(bool(c.get("exclude_rule")) for c in out)
    return {"crashes": out, "cleaning": log, "source": SOURCE, "years": years,
            "pulled_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# -- cache + API -------------------------------------------------------------------------------------
def get_cached(db: Database, sid: str) -> dict | None:
    r = db.one("SELECT * FROM crash_pull WHERE study_id = ?", (sid,))
    return {**json.loads(r["payload"]), "cache_key": r["cache_key"]} if r else None


def ensure(db: Database, sid: str, ckan: Ckan, refresh: bool = False) -> tuple[dict, bool]:
    """(pull result, from_cache). Re-pulls when refreshed or when window/corridor changed."""
    study = study_mod.require(db, sid)
    net = network_mod.network(db, sid)
    key = cache_key(study, net) if net.get("line") else None
    cached = get_cached(db, sid)
    if cached and not refresh and cached["cache_key"] == key:
        return cached, True
    result = pull(study, net, ckan)
    from .placement import place_unmatched   # C4: place crashes without coordinates (locator validated in PR #16)
    place_unmatched(db, net, result)
    db.execute("INSERT OR REPLACE INTO crash_pull (study_id, cache_key, pulled_at, payload) VALUES (?,?,?,?)",
               (sid, key, result["pulled_at"], json.dumps(result)))
    return {**result, "cache_key": key}, False


def ckan_for(request: Request) -> Ckan:
    st = request.app.state
    return Ckan(getattr(st, "ckan", None), retries=getattr(st, "ckan_retries", 3))


router = APIRouter()


def summary(result: dict, from_cache: bool) -> dict:
    return {"count": len(result["crashes"]), "cleaning": result["cleaning"], "source": result["source"],
            "years": result["years"], "pulled_at": result["pulled_at"], "from_cache": from_cache}


@router.post("/studies/{sid}/crashes/pull")
def post_pull(sid: str, request: Request, refresh: bool = False) -> dict:
    db = request.app.state.db
    try:
        result, hit = ensure(db, sid, ckan_for(request), refresh)
    except CkanError as e:
        raise HTTPException(502, str(e)) from e
    except PullError as e:
        raise HTTPException(409, str(e)) from e
    return summary(result, hit)


@router.get("/studies/{sid}/crashes")
def get_crashes(sid: str, request: Request) -> dict:
    db = request.app.state.db
    study_mod.require(db, sid)
    cached = get_cached(db, sid)
    if not cached:
        raise HTTPException(404, "No crashes pulled yet for this study.")
    return {**summary(cached, True), "crashes": cached["crashes"]}
