"""C2 network: a drawn corridor → ordered study intersections and segments from OpenStreetMap.

Pipeline (all deterministic code):
1. Overpass: road ways within ~40 m of the drawn line (+ their nodes and tags). Cached in SQLite.
2. Corridor ways: ways that run *along* the line (nodes within 80 ft and direction within 25°).
3. Candidate nodes: nodes shared by a corridor way and any other road way, inside the study limits.
4. Cluster candidates along the line (a divided road gives two nodes per cross street) → one intersection each.
5. Control from OSM tags near the intersection: traffic_signals → signal, stop → stop, else unknown. Never guessed.
6. Segments: between adjacent *study* intersections (and the study limits A/B), lengths in feet along the line.

Data © OpenStreetMap contributors (ODbL).
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from typing import Callable

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import study as study_mod
from .db import Database
from .geo import FT_PER_MI, Polyline, angle_diff
from .names import street_key

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ROAD_CLASSES = ("motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|road|"
                "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link")
QUERY_RADIUS_M = 40       # ways this close to the drawn line are fetched
ALONG_FT = 80             # a node this close to the line is "on" the corridor (covers divided roads)
PARALLEL_DEG = 25         # a way segment within this angle of the line runs along it
CLUSTER_FT = 150          # nodes this close along the line can belong to one intersection
END_TOL_FT = 60           # an intersection this far past A or B still counts as the terminus
STUB_FT = 50              # no segment between a terminus and an intersection closer than this
CONTROL_FT = 120          # signal/stop tags this close to the intersection set its control

DEFAULT_RADIUS_FT = 250.0   # HSM / Caltrans intersection influence area (R2.4)
DEFAULT_BUFFER_FT = 100.0   # corridor buffer each side of the line; provisional default, see PR for #7


class NetworkError(RuntimeError):
    """Overpass failed. Never turned into an empty intersection list."""


# -- Overpass ----------------------------------------------------------------------------------------
def overpass_query(line: list[tuple[float, float]]) -> str:
    coords = ",".join(f"{lat:.6f},{lon:.6f}" for lat, lon in line)
    return (f'[out:json][timeout:90];'
            f'way(around:{QUERY_RADIUS_M},{coords})["highway"~"^({ROAD_CLASSES})$"];'
            f'out body;>;out body qt;')


def _http_post(url: str, data: bytes, timeout: float) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "CrashIQ/0.1 (+crash safety analysis)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


Transport = Callable[[str, bytes, float], bytes]


def fetch_overpass(db: Database, query: str, transport: Transport | None = None, retries: int = 3,
                   backoff_s: float = 2.0, sleep: Callable[[float], None] = time.sleep) -> dict:
    """Overpass JSON for `query`, from the SQLite cache when present. Raises NetworkError on failure."""
    key = "overpass:" + hashlib.sha1(query.encode()).hexdigest()
    hit = db.one("SELECT body FROM http_cache WHERE key = ?", (key,))
    if hit:
        return json.loads(hit["body"])
    transport = transport or _http_post
    payload = urllib.parse.urlencode({"data": query}).encode()
    last = "no response"
    for attempt in range(retries + 1):
        try:
            data = json.loads(transport(OVERPASS_URL, payload, 120))
            if not isinstance(data.get("elements"), list):
                raise ValueError("response has no elements")
            remark = str(data.get("remark", ""))
            if "error" in remark.lower():          # Overpass reports timeouts as 200 + remark
                raise ValueError(remark)
            db.execute("INSERT OR REPLACE INTO http_cache (key, source, body) VALUES (?, 'overpass', ?)",
                       (key, json.dumps(data)))
            return data
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code not in (429, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            last = str(e) or type(e).__name__
        if attempt < retries:
            sleep(backoff_s * 2 ** attempt)
    raise NetworkError(f"Couldn't get streets from OpenStreetMap (Overpass): {last}. Try again in a minute.")


# -- detection ---------------------------------------------------------------------------------------
def _names(tags: dict) -> list[str]:
    out = []
    for t in ("name", "ref"):
        for v in str(tags.get(t, "")).split(";"):
            v = v.strip()
            if v and v not in out:
                out.append(v)
    return out


def _core(name: str) -> str | None:
    k = street_key(name)
    return k.core.replace(" ", "") if k else None


def detect(osm: dict, line_ll: list[tuple[float, float]]) -> dict:
    """Intersections along the drawn line, in order from its start (A) to its end (B)."""
    line = Polyline(line_ll)
    nodes: dict[int, dict] = {}
    ways: list[dict] = []
    for el in osm.get("elements", []):
        if el.get("type") == "node" and "lat" in el:
            nodes[el["id"]] = el
        elif el.get("type") == "way":
            ways.append(el)
    proj = {nid: line.project(n["lat"], n["lon"]) for nid, n in nodes.items()}

    # 2. corridor ways: enough of the way runs along the line
    corridor_ids: set[int] = set()
    along_len: Counter = Counter()
    for w in ways:
        near_len = run_len = 0.0
        for a, b in zip(w.get("nodes", []), w.get("nodes", [])[1:]):
            pa, pb = proj.get(a), proj.get(b)
            if pa is None or pb is None or pa.offset_ft > ALONG_FT or pb.offset_ft > ALONG_FT:
                continue
            seg = math.hypot(pb.x - pa.x, pb.y - pa.y)
            if seg == 0:
                continue
            near_len += seg
            ax, ay = line.proj.to_xy(nodes[a]["lat"], nodes[a]["lon"])
            bx, by = line.proj.to_xy(nodes[b]["lat"], nodes[b]["lon"])
            brg = math.degrees(math.atan2(bx - ax, by - ay)) % 180
            if angle_diff(brg, line.bearing_at(pa.index)) <= PARALLEL_DEG:
                run_len += seg
        if run_len >= 50 and run_len >= 0.5 * near_len:
            corridor_ids.add(w["id"])
            for n in _names(w.get("tags", {})):
                along_len[n] += run_len
    corridor_name = along_len.most_common(1)[0][0] if along_len else None
    corridor_cores = {c for c in (_core(n) for n in along_len) if c}

    # 3. candidate nodes
    corridor_nodes: set[int] = set()
    for w in ways:
        if w["id"] in corridor_ids:
            corridor_nodes.update(w.get("nodes", []))
    cross_names: dict[int, list[str]] = defaultdict(list)
    is_candidate: set[int] = set()
    for w in ways:
        if w["id"] in corridor_ids:
            continue
        names = [n for n in _names(w.get("tags", {})) if _core(n) not in corridor_cores]
        for nid in w.get("nodes", []):
            if nid in corridor_nodes and nid in proj:
                p = proj[nid]
                if p.offset_ft <= ALONG_FT and -END_TOL_FT <= p.station_ft <= line.length_ft + END_TOL_FT:
                    is_candidate.add(nid)
                    for n in names:
                        if n not in cross_names[nid]:
                            cross_names[nid].append(n)

    # 4. cluster along the line
    cands = sorted(is_candidate, key=lambda n: proj[n].station_ft)
    clusters: list[list[int]] = []
    for nid in cands:
        if clusters:
            last = clusters[-1]
            near = proj[nid].station_ft - proj[last[-1]].station_ft <= CLUSTER_FT
            a = {_core(x) for x in cross_names[nid]}
            b = {_core(x) for m in last for x in cross_names[m]}
            same_street = not a or not b or bool(a & b)
            if near and same_street:
                last.append(nid)
                continue
        clusters.append([nid])

    # 5. intersections with control from tags
    tagged = [(n, n.get("tags", {}).get("highway")) for n in nodes.values()]
    signals = [n for n, h in tagged if h == "traffic_signals"]
    stops = [n for n, h in tagged if h == "stop"]
    out = []
    for c in clusters:
        # Position from the nodes where a *named* cross street meets the corridor; unnamed slip lanes and
        # links join the cluster (and its node list) but don't pull the pin off the intersection.
        core = [n for n in c if cross_names[n]] or c
        st = sum(proj[n].station_ft for n in core) / len(core)
        # centroid of the actual OSM nodes (not the foot on the line), so the pin sits on the street
        cx = sum(line.proj.to_xy(nodes[n]["lat"], nodes[n]["lon"])[0] for n in core) / len(core)
        cy = sum(line.proj.to_xy(nodes[n]["lat"], nodes[n]["lon"])[1] for n in core) / len(core)
        lat, lon = line.proj.to_ll(cx, cy)
        names: Counter = Counter()
        for n in c:
            names.update(cross_names[n])
        name = " / ".join(n for n, _ in names.most_common()) or "Unnamed road"

        control = ("signal" if _any_within(line, signals, cx, cy, CONTROL_FT)
                   else "stop" if _any_within(line, stops, cx, cy, CONTROL_FT) else "unknown")
        out.append({
            "id": f"osm-{min(c)}", "name": name, "station_ft": round(max(0.0, min(line.length_ft, st)), 1),
            "lat": round(lat, 7), "lon": round(lon, 7), "osm_node_ids": sorted(c), "control": control,
            "is_study": True, "provenance": "auto", "name_source": "osm",
        })
    return {"corridor_name": corridor_name, "length_ft": round(line.length_ft, 1), "intersections": out}


def _any_within(line: Polyline, pts: list[dict], cx: float, cy: float, ft: float) -> bool:
    for p in pts:
        x, y = line.proj.to_xy(p["lat"], p["lon"])
        if math.hypot(x - cx, y - cy) <= ft:
            return True
    return False


def segments(intersections: list[dict], length_ft: float) -> list[dict]:
    """Segments between adjacent study intersections and the study limits A/B, lengths along the line."""
    pts = [{"id": "A", "name": "Study start (A)", "station_ft": 0.0}]
    pts += sorted((i for i in intersections if i["is_study"]), key=lambda i: i["station_ft"])
    pts += [{"id": "B", "name": "Study end (B)", "station_ft": length_ft}]
    if len(pts) > 2 and pts[1]["station_ft"] <= STUB_FT:
        pts.pop(0)
    if len(pts) > 2 and length_ft - pts[-2]["station_ft"] <= STUB_FT:
        pts.pop()
    out = []
    for a, b in zip(pts, pts[1:]):
        ft = b["station_ft"] - a["station_ft"]
        if ft <= 0:
            continue
        out.append({"id": f"seg:{a['id']}:{b['id']}", "from_id": a["id"], "to_id": b["id"],
                    "name": f"{a['name']} – {b['name']}", "from_station_ft": a["station_ft"],
                    "to_station_ft": b["station_ft"], "length_ft": round(ft, 1), "length_mi": round(ft / FT_PER_MI, 4)})
    return out


# -- storage -----------------------------------------------------------------------------------------
def _load(db: Database, sid: str) -> dict | None:
    c = db.one("SELECT * FROM corridor WHERE study_id = ?", (sid,))
    if not c:
        return None
    rows = db.query("SELECT * FROM intersection WHERE study_id = ? ORDER BY station_ft", (sid,))
    ints = [{**r, "is_study": bool(r["is_study"]), "osm_node_ids": json.loads(r["osm_node_ids"])} for r in rows]
    for i in ints:
        i.pop("study_id", None)
    aadt = {r["segment_id"]: r["aadt"] for r in db.query("SELECT * FROM segment_aadt WHERE study_id = ?", (sid,))}
    segs = segments(ints, c["length_ft"])
    for s in segs:
        s["aadt"] = aadt.get(s["id"])
    return {"line": json.loads(c["line_json"]), "length_ft": c["length_ft"],
            "length_mi": round(c["length_ft"] / FT_PER_MI, 4), "corridor_name": c["corridor_name"],
            "intersections": ints, "segments": segs, "detected_at": c["detected_at"]}


def network(db: Database, sid: str) -> dict:
    s = study_mod.require(db, sid)
    net = _load(db, sid)
    base = {"radius_ft": s["radius_ft"], "buffer_ft": s["buffer_ft"]}
    return {**base, **(net or {"line": None, "intersections": [], "segments": []})}


def save_corridor(db: Database, sid: str, line: list[tuple[float, float]], osm: dict) -> dict:
    found = detect(osm, line)
    with db.transaction() as conn:
        conn.execute("DELETE FROM intersection WHERE study_id = ?", (sid,))
        conn.execute("DELETE FROM segment_aadt WHERE study_id = ?", (sid,))
        conn.execute("INSERT OR REPLACE INTO corridor (study_id, line_json, length_ft, corridor_name, detected_at) "
                     "VALUES (?, ?, ?, ?, datetime('now'))",
                     (sid, json.dumps([list(p) for p in line]), found["length_ft"], found["corridor_name"]))
        for i in found["intersections"]:
            conn.execute("INSERT INTO intersection (study_id, id, name, station_ft, lat, lon, osm_node_ids, control, "
                         "is_study, provenance, name_source) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (sid, i["id"], i["name"], i["station_ft"], i["lat"], i["lon"], json.dumps(i["osm_node_ids"]),
                          i["control"], 1, "auto", "osm"))
    return network(db, sid)


def _line(db: Database, sid: str) -> Polyline:
    c = db.one("SELECT line_json FROM corridor WHERE study_id = ?", (sid,))
    if not c:
        raise HTTPException(409, "Draw the corridor first.")
    return Polyline([tuple(p) for p in json.loads(c["line_json"])])


def add_intersection(db: Database, sid: str, lat: float, lon: float, name: str) -> dict:
    line = _line(db, sid)
    p = line.project(lat, lon)
    if p.station_ext < -END_TOL_FT or p.station_ext > line.length_ft + END_TOL_FT:
        raise ValueError("That point is outside the study limits (A–B).")
    name = (name or "").strip() or "New intersection"
    iid = "usr-" + uuid.uuid4().hex[:8]
    db.execute("INSERT INTO intersection (study_id, id, name, station_ft, lat, lon, osm_node_ids, control, is_study, "
               "provenance, name_source) VALUES (?,?,?,?,?,?,'[]','unknown',1,'manual','user')",
               (sid, iid, name, round(max(0.0, min(line.length_ft, p.station_ft)), 1), lat, lon))
    return network(db, sid)


def edit_intersection(db: Database, sid: str, iid: str, changes: dict) -> dict:
    cur = db.one("SELECT * FROM intersection WHERE study_id = ? AND id = ?", (sid, iid))
    if not cur:
        raise HTTPException(404, "Intersection not found.")
    sets, vals = [], []
    if "name" in changes:
        name = (changes["name"] or "").strip()
        if not name:
            raise ValueError("The intersection needs a name.")
        sets += ["name = ?", "name_source = 'user'"]
        vals.append(name)
    if "is_study" in changes:
        sets.append("is_study = ?")
        vals.append(int(bool(changes["is_study"])))
    for k in ("major_aadt", "minor_aadt"):
        if k in changes:
            v = changes[k]
            if v is not None and v < 0:
                raise ValueError("AADT can't be negative.")
            sets.append(f"{k} = ?")
            vals.append(v)
    if sets:
        db.execute(f"UPDATE intersection SET {', '.join(sets)} WHERE study_id = ? AND id = ?", (*vals, sid, iid))
    return network(db, sid)


def remove_intersection(db: Database, sid: str, iid: str) -> dict:
    if db.execute("DELETE FROM intersection WHERE study_id = ? AND id = ?", (sid, iid)) == 0:
        raise HTTPException(404, "Intersection not found.")
    return network(db, sid)


def set_segment_aadt(db: Database, sid: str, seg_id: str, aadt: float | None) -> dict:
    if aadt is not None and aadt < 0:
        raise ValueError("AADT can't be negative.")
    if aadt is None:
        db.execute("DELETE FROM segment_aadt WHERE study_id = ? AND segment_id = ?", (sid, seg_id))
    else:
        db.execute("INSERT OR REPLACE INTO segment_aadt (study_id, segment_id, aadt) VALUES (?,?,?)", (sid, seg_id, aadt))
    return network(db, sid)


def clear_corridor(db: Database, sid: str) -> dict:
    with db.transaction() as conn:
        for t in ("intersection", "segment_aadt", "corridor"):
            conn.execute(f"DELETE FROM {t} WHERE study_id = ?", (sid,))
    return network(db, sid)


# -- API ---------------------------------------------------------------------------------------------
class CorridorIn(BaseModel):
    line: list[tuple[float, float]] = Field(min_length=2, max_length=500)


class IntersectionIn(BaseModel):
    lat: float
    lon: float
    name: str = ""


class IntersectionPatch(BaseModel):
    name: str | None = None
    is_study: bool | None = None
    major_aadt: float | None = None
    minor_aadt: float | None = None


class SegmentPatch(BaseModel):
    aadt: float | None = None


router = APIRouter()


def _db(request: Request) -> Database:
    return request.app.state.db


@router.get("/studies/{sid}/network")
def get_network(sid: str, request: Request) -> dict:
    return network(_db(request), sid)


@router.put("/studies/{sid}/corridor")
def put_corridor(sid: str, body: CorridorIn, request: Request) -> dict:
    db = _db(request)
    study_mod.require(db, sid)
    for lat, lon in body.line:
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Line points must be (lat, lon) in degrees.")
    try:
        st = request.app.state
        osm = fetch_overpass(db, overpass_query(body.line), transport=getattr(st, "overpass", None),
                             retries=getattr(st, "overpass_retries", 3))
    except NetworkError as e:
        raise HTTPException(502, str(e)) from e
    return save_corridor(db, sid, body.line, osm)


@router.delete("/studies/{sid}/corridor")
def delete_corridor(sid: str, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return clear_corridor(_db(request), sid)


@router.post("/studies/{sid}/intersections", status_code=201)
def post_intersection(sid: str, body: IntersectionIn, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return add_intersection(_db(request), sid, body.lat, body.lon, body.name)


@router.patch("/studies/{sid}/intersections/{iid}")
def patch_intersection(sid: str, iid: str, body: IntersectionPatch, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return edit_intersection(_db(request), sid, iid, body.model_dump(exclude_unset=True))


@router.delete("/studies/{sid}/intersections/{iid}")
def delete_intersection(sid: str, iid: str, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return remove_intersection(_db(request), sid, iid)


@router.patch("/studies/{sid}/segments/{seg_id}")
def patch_segment(sid: str, seg_id: str, body: SegmentPatch, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return set_segment_aadt(_db(request), sid, seg_id, body.aadt)
