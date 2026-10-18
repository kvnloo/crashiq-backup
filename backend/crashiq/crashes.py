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

from . import network as network_mod
from . import study as study_mod
from .db import Database
from .geo import LocalProjection
from .names import street_key
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


def cache_key(study: dict, net: dict) -> str:
    raw = json.dumps([study["from_year"], study["to_year"], net["line"], net.get("corridor_name"), margin_ft(study)])
    return hashlib.sha1(raw.encode()).hexdigest()


def _select(cols: dict[str, dict]) -> str:
    return ", ".join(cc.q(f["id"]) for f in cols.values())


def _paged(ckan: Ckan, sql_head: str, order_col: str) -> list[dict]:
    out, offset = [], 0
    while True:
        batch = ckan.sql(f"{sql_head} ORDER BY {order_col} LIMIT {PAGE} OFFSET {offset}")
        out += batch
        if len(batch) < PAGE:
            return out
        offset += PAGE


def _corridor_cores(net: dict) -> list[str]:
    k = street_key(net.get("corridor_name"))
    return [k.core] if k else []


def _cross_cores(net: dict, cores: list[str]) -> list[str]:
    """Cross-street name cores from the corridor's intersections (e.g. 'ROSE', 'DELORES')."""
    out = []
    for i in net.get("intersections") or []:
        for part in str(i.get("name") or "").replace("/", "&").split("&"):
            k = street_key(part)
            if k and k.core not in cores and k.core not in out and len(k.core) >= 3:
                out.append(k.core)
    return out


def _cities_by_street_names(ckan: Ckan, head: str, cols: dict, no_xy_where: str, cores: list[str],
                            cross: list[str]) -> list[str]:
    """When no GPS crash is near the corridor (e.g. Union City PD records GPS on 0% of reports), find the
    corridor's city from the reports themselves: crashes naming the corridor street AND one of its cross streets.
    Cities with >= 2 such crashes (or the single best city) are searched. 2026-10-18, user's Union City study."""
    if not cores or not cross or "city_code" not in cols:
        return []
    pr, sr = cc.q(cols["primary_road"]["id"]), cc.q(cols["secondary_road"]["id"])
    like = lambda col, words: " OR ".join(f"UPPER({col}) LIKE '%{w.replace(chr(39), '')}%'" for w in words)
    pair = f"(({like(pr, cores)}) AND ({like(sr, cross)})) OR (({like(sr, cores)}) AND ({like(pr, cross)}))"
    code = cc.q(cols["city_code"]["id"])
    rows = ckan.sql(f"SELECT {code} AS city_code, COUNT(*) AS n FROM {head.split(' FROM ', 1)[1]} "
                    f"WHERE {no_xy_where} AND ({pair}) GROUP BY {code} ORDER BY n DESC LIMIT 20")
    rows = [(str(r["city_code"]).strip(), int(r["n"])) for r in rows if r.get("city_code")]
    if not rows:
        return []
    keep = [c for c, n in rows if n >= 2]
    return keep or [rows[0][0]]


def _by_ids(ckan: Ckan, rid: str, cols: dict[str, dict], ids: list[str]) -> list[dict]:
    idcol = cols["collision_id"]
    rows = []
    for i in range(0, len(ids), ID_CHUNK):
        chunk = ids[i:i + ID_CHUNK]
        lit = ", ".join(str(int(x)) if str(x).isdigit() else "'" + str(x).replace("'", "''") + "'" for x in chunk)
        rows += ckan.sql(f"SELECT {_select(cols)} FROM {cc.q(rid)} WHERE {cc.q(idcol['id'])} IN ({lit})")
    return rows


def pull(study: dict, net: dict, ckan: Ckan) -> dict:
    if not net.get("line"):
        raise PullError("Draw the corridor first.")
    years = list(range(study["from_year"], study["to_year"] + 1))
    res = cc.table_resources(ckan.get("package_show", id=cc.PACKAGE))
    log = {"rows_read": 0, "outside_window_dropped": 0, "deleted_dropped": 0, "duplicate_versions_dropped": 0,
           "no_coords_read": 0, "no_coords_not_corridor_street": 0, "preliminary_kept": 0,
           "feet_typed_as_miles_fixed": 0, "years_missing": [], "parties_missing_years": [], "iwp_missing_years": [],
           "missing_fields": {}, "unknown_injury_values": [], "cities": []}
    s, w, n, e = bbox(net["line"], margin_ft(study))
    cores = _corridor_cores(net)
    cross = _cross_cores(net, cores)
    name_cities: list[str] | None = None   # found once from street names, reused for every year
    log["city_source"] = None
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
        head = f"SELECT {_select(cols)} FROM {cc.q(rid)}"
        with_xy = _paged(ckan, f"{head} WHERE {lat} BETWEEN {s:.6f} AND {n:.6f} AND {lon} BETWEEN {w:.6f} AND {e:.6f}", cid)
        recs = [(cc.crash_record(r, cols), "gps") for r in with_xy]
        cities = sorted({r["city_code"] for r, _ in recs if r["city_code"]})
        log["cities"] = sorted(set(log["cities"]) | {r["city"] for r, _ in recs if r["city"]})
        no_xy_where = f"({lat} IS NULL OR {lat} = 0 OR {lon} IS NULL OR {lon} = 0)"
        if cities:
            log["city_source"] = log["city_source"] or "gps crashes near the corridor"
        elif cores:
            if name_cities is None or not name_cities:
                name_cities = _cities_by_street_names(ckan, head, cols, no_xy_where, cores, cross)
            cities = name_cities
            if cities:
                log["city_source"] = "street names (no GPS crashes near the corridor)"
        no_xy = []
        if cores and cities and "city_code" in cols:
            pr, sr = cc.q(cols["primary_road"]["id"]), cc.q(cols["secondary_road"]["id"])
            names = " OR ".join(f"UPPER({c}) LIKE '%{core.replace(chr(39), '')}%'" for core in cores for c in (pr, sr))
            city_in = ", ".join("'" + c.replace("'", "''") + "'" for c in cities)
            no_xy = _paged(ckan, f"{head} WHERE {no_xy_where} "
                                 f"AND {cc.q(cols['city_code']['id'])} IN ({city_in}) AND ({names})", cid)
            if not log["cities"]:
                log["cities"] = sorted({cc.crash_record(r, cols)["city"] for r in no_xy if cc.crash_record(r, cols)["city"]})
        log["no_coords_read"] += len(no_xy)
        for r in no_xy:
            c = cc.crash_record(r, cols)
            keys = [street_key(c["primary_road"]), street_key(c["secondary_road"])]
            if any(k and k.core in cores for k in keys):
                recs.append((c, "unmatched"))
            else:
                log["no_coords_not_corridor_street"] += 1
        log["rows_read"] += len(with_xy) + len(no_xy)
        raw_by_year[y] = recs

    # cleaning: window, CHP-deleted, duplicate report versions (keep the highest), preliminary flagged
    crashes: dict[str, dict] = {}
    dup_seen = 0
    for y, recs in raw_by_year.items():
        for c, loc in recs:
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
            for r in _by_ids(ckan, prid, pcols, ids):
                parties.setdefault(str(r[pcols["collision_id"]["id"]]), []).append(cc.party_record(r, pcols))
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
        log["warning"] = ("No crashes found. " + ("No city could be identified for this corridor (no GPS crashes nearby, "
                          "and no reports name the corridor street with one of its cross streets)."
                          if not log["city_source"] else "The corridor's city was found, but no report names this street."))
    log["with_coords"] = sum(c["location_source"] == "gps" for c in out)
    log["without_coords"] = sum(c["location_source"] == "unmatched" for c in out)
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
    from .placement import place_unmatched   # C4: place crashes without coordinates (validated in PR #16)
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
