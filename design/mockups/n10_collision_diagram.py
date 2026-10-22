"""N10 mock-up (not product code): one intersection's collision diagram from real Crenshaw crashes.

Layout follows DemandIQ's line-diagram cell (grey arms, control symbol, street names on the arms, approaches by
direction of travel, slots so nothing overlaps). Symbols follow standard collision-diagram practice: HSM Ch. 5
Exhibits 5-4/5-5 (adapted from ITE), NCDOT TEAAS, Region of Peel, Seattle SDOT. See docs/06-nuances.md, N10.

    python design/mockups/n10_collision_diagram.py <crashes.json> design/mockups/n10-collision-diagram.html
"""

from __future__ import annotations

import html
import json
import sys

SEV = {"K": "#e62b34", "A": "#fd811b", "B": "#f6c330", "C": "#5dacba", "U": "#8e9aa6", "O": "#686c71"}
INK, ARM, PAPER, MUTED = "#22282E", "#969696", "#FFFFFF", "#57636F"
ROT = {"N": 0, "E": 90, "S": 180, "W": 270}       # heading up = northbound; SVG rotates clockwise
DIR_WORD = {"N": "NB", "S": "SB", "E": "EB", "W": "WB"}
TYPE_LABEL = {"rear": "Rear-end", "angle": "Angle / broadside", "left": "Left turn, broadside",
              "head": "Head-on", "ss_same": "Sideswipe, same direction", "ss_opp": "Sideswipe, opposite direction",
              "object": "Fixed object", "ped": "Pedestrian", "bike": "Bicycle", "backing": "Backing",
              "parked": "Parked vehicle", "ooc": "Out of control / ran off road", "other": "Other / not stated"}


def rel(a: str | None, b: str | None) -> int | None:
    return None if a not in ROT or b not in ROT else (ROT[b] - ROT[a]) % 360


def classify(c: dict) -> tuple[str, dict, dict | None]:
    """Crash type for the symbol, the party drawn as the main arrow (at fault, else party 1), and the other moving
    vehicle. Mock-up rules; the real mapping is the N10 table in docs/06."""
    ps = [p for p in c["parties"] if p.get("direction") in ROT]
    veh = [p for p in ps if (p.get("party_type") or "").upper() != "PEDESTRIAN"]
    moving = [p for p in veh if (p.get("party_type") or "").upper() != "PARKEDVEHICLE"]
    atf = next((p for p in moving if p.get("at_fault")), None) or next(
        (p for p in moving if str(p.get("party_number")) == "1"), None) or (moving or veh or ps or [{}])[0]
    other = next((p for p in moving if p is not atf), None)
    mv = (atf.get("movement") or "").upper()
    ct = (c.get("collision_type") or "").upper()
    if c.get("ped"):
        return "ped", atf, other
    if c.get("bike") or c.get("ebike") or c.get("escooter"):
        return "bike", atf, other
    if other is None and any((p.get("party_type") or "").upper() == "PARKEDVEHICLE" for p in c["parties"]):
        return "parked", atf, other              # hit a parked vehicle, no other moving vehicle
    if "BACKING" in mv:
        return "backing", atf, other
    if "RAN OFF ROAD" in mv or "OVERTURN" in ct:
        return "ooc", atf, other
    if "REAR" in ct:
        return "rear", atf, other
    if "BROADSIDE" in ct:
        return ("left" if "LEFT" in mv else "angle"), atf, other
    if "HEAD" in ct:
        return "head", atf, other
    if "SIDE" in ct:
        return ("ss_opp" if rel(atf.get("direction"), (other or {}).get("direction")) == 180 else "ss_same"), atf, other
    if "OBJECT" in ct:
        return "object", atf, other
    return "other", atf, other


def head(x, y, ang, night, color=INK):
    """Arrowhead at (x, y) pointing along `ang` degrees (0 = up). Night: filled; day: hollow (NCDOT)."""
    return (f'<path d="M0,-4 L3.4,3 L-3.4,3 Z" transform="translate({x},{y}) rotate({ang})" '
            f'fill="{color if night else PAPER}" stroke="{color}" stroke-width="1.3" stroke-linejoin="round"/>')


def line(pts, dash=None, color=INK, w=1.6):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"{extra} '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def severity_mark(x, y, s):
    """At the impact point: filled circle fatal, hollow circle injury (ring in the severity colour), crossbar PDO."""
    if s == "K":
        return f'<circle cx="{x}" cy="{y}" r="4.2" fill="{SEV["K"]}" stroke="{INK}" stroke-width="1"/>'
    if s in "ABCU":
        return f'<circle cx="{x}" cy="{y}" r="4.2" fill="{PAPER}" stroke="{SEV[s]}" stroke-width="2.2"/>'
    return f'<path d="M{x - 5},{y} L{x + 5},{y}" stroke="{INK}" stroke-width="2.2" stroke-linecap="round"/>'


def glyph(kind, r_other, night, sev):
    """One crash, heading up, in a 48x48 box; impact point near (24, 16)."""
    out, ix, iy = [], 24, 16

    def main(end=(24, 18)):
        return [line([(24, 44), end]), head(end[0], end[1], 0, night)]
    if kind == "rear":
        out += main((24, 22)) + [line([(24, 12), (24, 3)]), head(24, 3, 0, night)]
    elif kind in ("angle", "ped", "bike"):
        left = r_other in (None, 90)                        # an eastbound other party comes from the left
        side, tip, ang = (6, 20, 90) if left else (42, 28, 270)
        out += main() + [line([(side, 16), (tip, 16)], dash="1.5 3" if kind == "ped" else None), head(tip, 16, ang, night)]
        if kind in ("ped", "bike"):
            out.append(f'<text x="{side}" y="11" font-size="8" font-weight="700" fill="{INK}" '
                       f'text-anchor="middle">{"P" if kind == "ped" else "B"}</text>')
    elif kind == "left":
        out += [line([(24, 44), (24, 22), (10, 16)]), head(10, 16, 290, night),
                line([(30, 2), (30, 12)]), head(30, 12, 180, night)]
        ix = 22
    elif kind == "head":
        out += main((24, 22)) + [line([(24, 2), (24, 10)]), head(24, 10, 180, night)]
    elif kind == "ss_same":
        out += [line([(18, 44), (22, 18)]), head(22, 18, 9, night), line([(32, 44), (26, 18)]), head(26, 18, -13, night)]
    elif kind == "ss_opp":
        out += [line([(20, 44), (22, 18)]), head(22, 18, 4, night), line([(30, 2), (26, 26)]), head(26, 26, 189, night)]
        iy = 22
    elif kind == "object":
        out += main((24, 20)) + [line([(15, 12), (15, 10), (33, 10), (33, 12)], w=2)]
        iy = 14
    elif kind == "parked":
        out += main((24, 20)) + [f'<rect x="28" y="6" width="12" height="16" fill="{PAPER}" stroke="{INK}" stroke-width="1.4"/>',
                                 line([(28, 6), (40, 22)], w=1), line([(40, 6), (28, 22)], w=1)]
        ix = 26
    elif kind == "backing":
        out += [line([(24, 44), (24, 12)])] + [head(24, y, 0, night) for y in (12, 20, 28)]
    elif kind == "ooc":
        out += [line([(24, 44), (18, 38), (30, 32), (18, 26), (24, 20)]), head(24, 18, 0, night)]
    else:
        out += main() + [f'<text x="34" y="14" font-size="9" fill="{INK}">?</text>']
    out.append(severity_mark(ix, iy, sev))
    return "".join(out)


def light_code(c):
    """HSM surface + light code (C dry, W wet, S snow/ice, O other; D day, N dark no lights, L dark with lights)."""
    surf = (c.get("surface") or "").upper()
    s = "W" if "WET" in surf else "S" if "SNOW" in surf or "ICY" in surf else "C" if "DRY" in surf else "O"
    lt = (c.get("lighting") or "").upper()
    lit = "STREET LIGHTS" in lt and "NO STREET" not in lt and "NOT FUNCTION" not in lt
    return s + ("L" if lit else "N" if "DARK" in lt else "D"), lt.startswith("DARK")


def build(data):
    c0 = data["intersection"]
    crashes = sorted(data["crashes"], key=lambda c: (c["date"] or "", c.get("hour") or 0))
    W = H = 820
    cx = cy = 410
    slot, start, cols, k_ = 66, 70, 3, 1.3       # glyphs drawn at 1.3x in 66 px slots
    # approach quadrants as in DemandIQ (right-hand traffic): SB west of the north arm, NB east of the south arm,
    # EB south of the west arm, WB north of the east arm; slots fill outward so glyphs never overlap
    base = {"S": (-1, -1), "N": (1, 1), "E": (-1, 1), "W": (1, -1)}
    used = {k: 0 for k in base}
    body, rows = [], []
    for n, c in enumerate(crashes, 1):
        kind, atf, other = classify(c)
        d = atf.get("direction") if atf.get("direction") in ROT else "N"
        code, night = light_code(c)
        k = used[d]
        used[d] += 1
        out_i, across = k // cols, k % cols
        sx, sy = base[d]
        if d in ("N", "S"):                      # stack along the N-S arm
            gx = cx + sx * (16 + across * slot) + (0 if sx > 0 else -48 * k_)
            gy = cy + sy * (start + out_i * slot) + (0 if sy > 0 else -48 * k_)
        else:                                    # stack along the E-W arm
            gx = cx + sx * (start + out_i * slot) + (0 if sx > 0 else -48 * k_)
            gy = cy + sy * (16 + across * slot) + (0 if sy > 0 else -48 * k_)
        r_other = rel(d, (other or {}).get("direction"))
        body.append(f'<g transform="translate({gx},{gy}) scale({k_})"><g transform="rotate({ROT[d]} 24 24)">'
                    f'{glyph(kind, r_other, night, c["severity"])}</g>'
                    f'<text x="-9" y="47" font-size="8" font-weight="700" fill="{MUTED}">{n}</text></g>')
        hour = f"{int(c['hour']):02d}00" if c.get("hour") is not None else "—"
        rows.append((n, c["date"], hour, DIR_WORD[d], TYPE_LABEL[kind], c["severity"], code))
    arms = "".join(line(p, color=ARM, w=3) for p in ([(cx, 20), (cx, H - 20)], [(20, cy), (W - 20, cy)]))
    labels = (f'<text x="{cx - 10}" y="40" font-size="13" font-weight="700" fill="{INK}" '
              f'transform="rotate(-90 {cx - 10} 40)" text-anchor="end">Crenshaw Blvd</text>'
              f'<text x="{W - 28}" y="{cy - 10}" font-size="13" font-weight="700" fill="{INK}" text-anchor="end">'
              f'{html.escape(c0["name"]).replace("West ", "W ").replace("Street", "St")}</text>')
    signal = f'<circle cx="{cx}" cy="{cy}" r="9" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
    north = (f'<g transform="translate({W - 44},70)"><path d="M0,-18 L7,4 L0,-2 L-7,4 Z" fill="{INK}"/>'
             f'<text x="0" y="18" font-size="11" font-weight="700" text-anchor="middle" fill="{INK}">N</text></g>')
    svg = (f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Collision diagram mock-up">'
           f'<rect width="{W}" height="{H}" fill="{PAPER}" stroke="{INK}"/>{arms}{signal}{labels}{north}'
           f'<text x="{cx}" y="{H - 8}" font-size="11" text-anchor="middle" fill="{MUTED}">Not to scale · each crash '
           f'drawn on the approach of the party at fault</text>' + "".join(body) + "</svg>")
    sev_count = {s: sum(r[5] == s for r in rows) for s in "KABCUO"}
    legend_items = [("rear", None), ("angle", 90), ("left", None), ("head", None), ("ss_same", None), ("ss_opp", None),
                    ("object", None), ("ped", 90), ("bike", 90), ("backing", None), ("parked", None), ("ooc", None)]
    legend = "".join(f'<div class="lg"><svg viewBox="0 0 48 48" width="44" height="44">{glyph(k, r, False, "C")}</svg>'
                     f'<span>{TYPE_LABEL[k]}</span></div>' for k, r in legend_items)
    mark = lambda inner: f'<svg viewBox="0 0 20 20" width="20" height="20">{inner}</svg>'
    sevleg = (f'<div class="lg">{mark(severity_mark(10, 10, "K"))}<span>Fatal (filled circle)</span></div>'
              f'<div class="lg">{mark(severity_mark(10, 10, "A"))}<span>Injury (hollow circle, ring in the severity colour)</span></div>'
              f'<div class="lg">{mark(severity_mark(10, 10, "O"))}<span>Property damage only (crossbar)</span></div>'
              f'<div class="lg">{mark(head(10, 10, 0, False))}<span>Day (hollow arrowhead)</span></div>'
              f'<div class="lg">{mark(head(10, 10, 0, True))}<span>Night (filled arrowhead)</span></div>')
    table = "".join(f"<tr><td>{n}</td><td>{d}</td><td>{h}</td><td>{a}</td><td>{t}</td><td>{s}</td><td>{code}</td></tr>"
                    for n, d, h, a, t, s, code in rows)
    title = f'Crenshaw Blvd @ {html.escape(c0["name"])}'
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>N10 collision diagram mock-up</title>
<style>body{{font:13px/1.4 Overpass,system-ui,sans-serif;color:{INK};background:#F4F5F7;margin:0;padding:24px}}
.wrap{{display:grid;grid-template-columns:{W}px 1fr;gap:24px;align-items:start}}h1{{font-size:18px;margin:0 0 4px}}
.sub{{color:{MUTED};margin:0 0 14px}}.panel{{background:#fff;border:1px solid #D3D8DD;border-radius:6px;padding:14px}}
.lgs{{display:grid;grid-template-columns:1fr 1fr;gap:4px 12px}}.lg{{display:flex;align-items:center;gap:8px}}
table{{border-collapse:collapse;width:100%;font:12px Overpass Mono,ui-monospace,monospace}}td,th{{padding:2px 6px;border-bottom:1px solid #eee;text-align:left}}
h2{{font-size:13px;margin:14px 0 8px}}</style></head><body>
<h1>{title}: collision diagram (mock-up, N10)</h1>
<p class="sub">CCRS 2021–2025 · {len(rows)} crashes at this intersection (fatal {sev_count['K']}, serious {sev_count['A']}, minor {sev_count['B']}, possible {sev_count['C']}, injury level not stated {sev_count['U']}, property damage only {sev_count['O']}) · Mock-up for the user's decision; not built.</p>
<div class="wrap"><div>{svg}</div><div class="panel"><h2 style="margin-top:0">Crash type (HSM / ITE symbols)</h2><div class="lgs">{legend}</div>
<h2>Severity and light</h2><div class="lgs">{sevleg}</div>
<h2>Crashes (number on the diagram)</h2><table><tr><th>#</th><th>Date</th><th>Time</th><th>Approach</th><th>Type</th><th>Sev.</th><th>Code</th></tr>{table}</table>
<p class="sub" style="margin-top:8px">Code = road surface + light (HSM): C dry, W wet, S snow/ice, O other · D daylight, N dark without street lights, L dark with street lights.</p></div></div></body></html>"""


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    with open(sys.argv[2], "w") as f:
        f.write(build(data))
