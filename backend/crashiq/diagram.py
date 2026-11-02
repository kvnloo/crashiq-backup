"""Collision diagram per study intersection (#106; user decision N10, docs/03 2026-10-21).

Layout follows DemandIQ's line-diagram cell: grey arms, the control symbol, street names on the arms, approaches by
direction of travel, slots that never overlap. Symbols follow standard collision-diagram practice (HSM Ch. 5 Exhibits
5-4/5-5 after ITE; NCDOT; Region of Peel; Seattle SDOT), as in docs/06 N10 revision 2:

- each crash is drawn on the approach of the party at fault (else party 1), in that approach's quadrant;
- severity at the impact point: filled circle = fatal, hollow circle = injury (ring in the KABCO colour), crossbar =
  property damage only; arrowheads hollow by day, filled in the dark, plus HSM's surface + light code in the list;
- NCDOT stacking: identical crashes (same type, approach, side of the other party, road surface and light code) share
  one symbol with a row of crash numbers; the symbol carries the most severe mark among them;
- crashes are numbered in date order, keyed to the crash list (table T21@<location>).

Code computes every placement; the output is a list of drawing steps (lines, arrowheads, circles, rectangles, text)
in one 820 x 820 coordinate frame, drawn as SVG by the app and with ReportLab in the PDF, so both always match.
"""

from __future__ import annotations

import math

ROT = {"N": 0, "E": 90, "S": 180, "W": 270}         # heading up = northbound
DIR_WORD = {"N": "NB", "S": "SB", "E": "EB", "W": "WB"}
TYPE_LABEL = {"rear": "Rear-end", "angle": "Angle / broadside", "left": "Left turn, broadside",
              "head": "Head-on", "ss_same": "Sideswipe, same direction", "ss_opp": "Sideswipe, opposite direction",
              "object": "Fixed object", "ped": "Pedestrian", "bike": "Bicycle", "backing": "Backing",
              "parked": "Parked vehicle", "ooc": "Out of control / ran off road", "other": "Other / not stated"}
SEV_RANK = "KABCUO"
W = H = 820
CX = CY = 410
SLOT, START, COLS, SCALE = 66, 70, 3, 1.3
QUADRANT = {"S": (-1, -1), "N": (1, 1), "E": (-1, 1), "W": (1, -1)}   # right-hand traffic (DemandIQ)
MAX_ROWS = 5                                         # slots per quadrant column before the cell edge


def _rel(a, b):
    return None if a not in ROT or b not in ROT else (ROT[b] - ROT[a]) % 360


def classify(c: dict) -> tuple[str, dict, dict | None]:
    """(symbol type, party drawn as the main arrow, the other moving vehicle) from CCRS collision type, movement and
    party types (N10 revision 2 table)."""
    ps = [p for p in c.get("parties") or [] if p.get("direction") in ROT]
    veh = [p for p in ps if (p.get("party_type") or "").upper() != "PEDESTRIAN"]
    moving = [p for p in veh if (p.get("party_type") or "").upper() != "PARKEDVEHICLE"]
    atf = next((p for p in moving if p.get("at_fault")), None) or next(
        (p for p in moving if str(p.get("party_number")) == "1"), None) or (moving or veh or ps or [{}])[0]
    other = next((p for p in moving if p is not atf), None)
    mv = (atf.get("movement") or "").upper()
    ct = (c.get("collision_type") or "").upper()
    if c.get("ped") or "PEDESTR" in ct:
        kind = "ped"
    elif c.get("bike") or c.get("ebike") or c.get("escooter"):
        kind = "bike"
    elif other is None and any((p.get("party_type") or "").upper() == "PARKEDVEHICLE" for p in c.get("parties") or []):
        kind = "parked"
    elif "BACKING" in mv:
        kind = "backing"
    elif "RAN OFF ROAD" in mv or "OVERTURN" in ct:
        kind = "ooc"
    elif "REAR" in ct:
        kind = "rear"
    elif "BROADSIDE" in ct:
        kind = "left" if "LEFT" in mv else "angle"
    elif "HEAD" in ct:
        kind = "head"
    elif "SIDE" in ct:
        kind = "ss_opp" if _rel(atf.get("direction"), (other or {}).get("direction")) == 180 else "ss_same"
    elif "OBJECT" in ct:
        kind = "object"
    else:
        kind = "other"
    return kind, atf, other


def light_code(c: dict) -> tuple[str, bool]:
    """HSM surface + light code (C dry, W wet, S snow/ice, O other; D day, N dark no lights, L dark with lights)."""
    surf = (c.get("surface") or "").upper()
    s = "W" if "WET" in surf else "S" if "SNOW" in surf or "ICY" in surf else "C" if "DRY" in surf else "O"
    lt = (c.get("lighting") or "").upper()
    lit = "STREET LIGHTS" in lt and "NO STREET" not in lt and "NOT FUNCTION" not in lt
    return s + ("L" if lit else "N" if "DARK" in lt else "D"), lt.startswith("DARK")


# -- glyphs: drawing steps in a 48 x 48 box, heading up ----------------------------------------------------
def _line(pts, dash=False, w=1.6):
    return {"op": "line", "pts": [list(p) for p in pts], "dash": dash, "w": w, "color": "ink"}


def _head(x, y, ang, night):
    return {"op": "head", "x": x, "y": y, "ang": ang, "filled": night, "color": "ink"}


def severity_mark(x, y, s):
    if s == "K":
        return [{"op": "circle", "x": x, "y": y, "r": 4.2, "fill": "sev_k", "stroke": "ink", "w": 1}]
    if s in "ABCU":
        return [{"op": "circle", "x": x, "y": y, "r": 4.2, "fill": "paper", "stroke": f"sev_{s.lower()}", "w": 2.2}]
    return [{"op": "line", "pts": [[x - 5, y], [x + 5, y]], "dash": False, "w": 2.2, "color": "ink"}]


def glyph(kind, r_other, night, sev) -> list[dict]:
    out, ix, iy = [], 24, 16

    def main(end=(24, 18)):
        return [_line([(24, 44), end]), _head(end[0], end[1], 0, night)]
    if kind == "rear":
        out += main((24, 22)) + [_line([(24, 12), (24, 3)]), _head(24, 3, 0, night)]
    elif kind in ("angle", "ped", "bike"):
        left = r_other in (None, 90)
        side, tip, ang = (6, 20, 90) if left else (42, 28, 270)
        out += main() + [_line([(side, 16), (tip, 16)], dash=kind == "ped"), _head(tip, 16, ang, night)]
        if kind in ("ped", "bike"):
            out.append({"op": "text", "x": side, "y": 11, "t": "P" if kind == "ped" else "B", "size": 8, "bold": True,
                        "anchor": "middle", "color": "ink"})
    elif kind == "left":
        out += [_line([(24, 44), (24, 22), (10, 16)]), _head(10, 16, 290, night),
                _line([(30, 2), (30, 12)]), _head(30, 12, 180, night)]
        ix = 22
    elif kind == "head":
        out += main((24, 22)) + [_line([(24, 2), (24, 10)]), _head(24, 10, 180, night)]
    elif kind == "ss_same":
        out += [_line([(18, 44), (22, 18)]), _head(22, 18, 9, night), _line([(32, 44), (26, 18)]), _head(26, 18, -13, night)]
    elif kind == "ss_opp":
        out += [_line([(20, 44), (22, 18)]), _head(22, 18, 4, night), _line([(30, 2), (26, 26)]), _head(26, 26, 189, night)]
        iy = 22
    elif kind == "object":
        out += main((24, 20)) + [_line([(15, 12), (15, 10), (33, 10), (33, 12)], w=2)]
        iy = 14
    elif kind == "parked":
        out += main((24, 20)) + [{"op": "rect", "x": 28, "y": 6, "w": 12, "h": 16, "stroke": "ink", "fill": "paper"},
                                 _line([(28, 6), (40, 22)], w=1), _line([(40, 6), (28, 22)], w=1)]
        ix = 26
    elif kind == "backing":
        out += [_line([(24, 44), (24, 12)])] + [_head(24, y, 0, night) for y in (12, 20, 28)]
    elif kind == "ooc":
        out += [_line([(24, 44), (18, 38), (30, 32), (18, 26), (24, 20)]), _head(24, 18, 0, night)]
    else:
        out += main() + [{"op": "text", "x": 34, "y": 14, "t": "?", "size": 9, "bold": False, "anchor": "start",
                          "color": "ink"}]
    return out + severity_mark(ix, iy, sev)


def _place(ops: list[dict], rot: float, gx: float, gy: float, k: float) -> list[dict]:
    """Rotate a 48x48 glyph about its centre by `rot` degrees, scale by k, move to (gx, gy): absolute steps."""
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)

    def tr(x, y):
        dx, dy = x - 24, y - 24
        return round(gx + k * (24 + dx * ca - dy * sa), 2), round(gy + k * (24 + dx * sa + dy * ca), 2)
    out = []
    for o in ops:
        o = dict(o)
        if o["op"] == "line":
            o["pts"] = [list(tr(*p)) for p in o["pts"]]
            o["w"] = o["w"] * k
        elif o["op"] in ("head", "circle", "text"):
            o["x"], o["y"] = tr(o["x"], o["y"])
            if o["op"] == "head":
                o["ang"] = (o["ang"] + rot) % 360
                o["size"] = k
            if o["op"] == "circle":
                o["r"] *= k
                o["w"] *= k
            if o["op"] == "text":
                o["size"] *= k
        elif o["op"] == "rect":                         # a parked box: becomes a polygon
            x, y, w, h = o["x"], o["y"], o["w"], o["h"]
            o = {"op": "poly", "pts": [list(tr(*p)) for p in ((x, y), (x + w, y), (x + w, y + h), (x, y + h))],
                 "stroke": o["stroke"], "fill": o["fill"], "w": 1.4 * k}
        out.append(o)
    return out


def _arm_names(net: dict, it: dict) -> tuple[str, str, bool]:
    """(N-S arm name, E-W arm name, corridor runs N-S): the corridor on the arm nearest its own bearing here."""
    line = net["line"]
    lat0 = math.radians(sum(p[0] for p in line) / len(line))
    dx = (line[-1][1] - line[0][1]) * math.cos(lat0)
    dy = line[-1][0] - line[0][0]
    ns = abs(dy) >= abs(dx)
    corridor = net.get("corridor_name") or "Corridor"
    cross = str(it.get("name") or "")
    return (corridor, cross, True) if ns else (cross, corridor, False)


def build(net: dict, it: dict, crashes: list[dict]) -> dict:
    """Diagram for one study intersection: {"steps": [...], "crashes": [...numbered list...], "stacks": n,
    "not_drawn": n}. `crashes` are the crashes counted at this intersection, with parties."""
    rows = []
    for c in sorted(crashes, key=lambda c: (c.get("date") or "", c.get("hour") if c.get("hour") is not None else -1,
                                            c["crash_id"])):
        kind, atf, other = classify(c)
        d = atf.get("direction") if atf.get("direction") in ROT else None
        code, night = light_code(c)
        rows.append({"crash_id": c["crash_id"], "date": c.get("date"), "hour": c.get("hour"), "approach": d,
                     "type": kind, "severity": c.get("severity") or "O", "code": code, "night": night,
                     "r_other": _rel(d, (other or {}).get("direction"))})
    for n, r in enumerate(rows, 1):
        r["n"] = n
    # NCDOT stacking: identical crashes share one symbol
    stacks: dict[tuple, list] = {}
    for r in rows:
        if r["approach"] is None:
            continue
        stacks.setdefault((r["approach"], r["type"], r["r_other"], r["code"]), []).append(r)
    steps = [{"op": "rect_cell", "w": W, "h": H}]
    steps += [{"op": "line", "pts": [[CX, 20], [CX, H - 20]], "dash": False, "w": 3, "color": "arm"},
              {"op": "line", "pts": [[20, CY], [W - 20, CY]], "dash": False, "w": 3, "color": "arm"}]
    control = str(it.get("control") or "").lower()
    if "signal" in control:
        steps.append({"op": "circle", "x": CX, "y": CY, "r": 9, "fill": "paper", "stroke": "ink", "w": 2})
    elif control == "roundabout":                          # a ring in the middle (#337)
        steps.append({"op": "circle", "x": CX, "y": CY, "r": 18, "fill": "paper", "stroke": "ink", "w": 2})
    else:
        steps.append({"op": "circle", "x": CX, "y": CY, "r": 3, "fill": "ink", "stroke": "ink", "w": 1})
    ns_name, ew_name, _ = _arm_names(net, it)
    steps += [{"op": "text", "x": CX - 10, "y": 40, "t": ns_name, "size": 13, "bold": True, "anchor": "end", "rot": -90,
               "color": "ink"},
              {"op": "text", "x": W - 28, "y": CY - 10, "t": ew_name, "size": 13, "bold": True, "anchor": "end",
               "color": "ink"},
              {"op": "north", "x": W - 44, "y": 70},
              {"op": "text", "x": CX, "y": H - 8, "t": "Not to scale · each crash drawn on the approach of the party at "
               "fault · identical crashes stacked (NCDOT)", "size": 11, "bold": False, "anchor": "middle",
               "color": "muted"}]
    used = {k: 0 for k in QUADRANT}
    # crashes with no direction of travel can't be drawn: listed only, with why (no party data for that year in the pull)
    no_dir = [r for r in rows if r["approach"] is None]
    no_parties = {c["crash_id"] for c in crashes if not c.get("parties")}
    not_drawn = {"no_party_data": sum(r["crash_id"] in no_parties for r in no_dir),
                 "no_direction": sum(r["crash_id"] not in no_parties for r in no_dir), "no_room": 0}
    order = sorted(stacks.values(), key=lambda s: s[0]["n"])
    for s in order:
        d = s[0]["approach"]
        k = used[d]
        if k >= COLS * MAX_ROWS:
            not_drawn["no_room"] += len(s)
            continue
        used[d] += 1
        out_i, across = k // COLS, k % COLS
        sx, sy = QUADRANT[d]
        if d in ("N", "S"):
            gx = CX + sx * (16 + across * SLOT) + (0 if sx > 0 else -48 * SCALE)
            gy = CY + sy * (START + out_i * SLOT) + (0 if sy > 0 else -48 * SCALE)
        else:
            gx = CX + sx * (START + out_i * SLOT) + (0 if sx > 0 else -48 * SCALE)
            gy = CY + sy * (16 + across * SLOT) + (0 if sy > 0 else -48 * SCALE)
        worst = min((r["severity"] for r in s), key=lambda v: SEV_RANK.index(v) if v in SEV_RANK else 9)
        steps += _place(glyph(s[0]["type"], s[0]["r_other"], s[0]["night"], worst), ROT[d], gx, gy, SCALE)
        steps.append({"op": "text", "x": round(gx - 9 * SCALE, 2), "y": round(gy + 47 * SCALE, 2),
                      "t": ", ".join(str(r["n"]) for r in s), "size": 8 * SCALE if len(s) == 1 else 7 * SCALE,
                      "bold": True, "anchor": "start", "color": "muted"})
    for r in rows:
        r["approach"] = DIR_WORD.get(r["approach"], "—")
        r["type_label"] = TYPE_LABEL[r["type"]] if r["approach"] != "—" else "Not drawn (no direction of travel)"
    return {"steps": steps, "crashes": rows, "stacks": len(stacks), "not_drawn": not_drawn, "width": W, "height": H,
            "legend": legend(sorted({r["type"] for r in rows if r["approach"] in DIR_WORD.values()}))}


def legend(kinds: list[str]) -> dict:
    """Symbols used on this diagram plus the severity and light marks, each as steps in a 48 x 48 box."""
    sym = [{"key": k, "label": TYPE_LABEL[k], "steps": glyph(k, 90, False, "C")} for k in TYPE_LABEL if k in kinds]
    marks = [{"key": "K", "label": "Fatal (filled circle)", "steps": severity_mark(24, 24, "K")},
             {"key": "A", "label": "Injury (hollow circle, ring in the severity colour)", "steps": severity_mark(24, 24, "A")},
             {"key": "O", "label": "Property damage only (crossbar)", "steps": severity_mark(24, 24, "O")},
             {"key": "day", "label": "Day (hollow arrowhead)", "steps": [_head(24, 24, 0, False)]},
             {"key": "night", "label": "Night (filled arrowhead)", "steps": [_head(24, 24, 0, True)]}]
    return {"symbols": sym, "marks": marks}
