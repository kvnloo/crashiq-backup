"""Which Caltrans ramp a ramp crash is on (#287 ramps; user decision 2026-10-30, docs/03, #300: option B).

A crash is a ramp crash when its report names a ramp. Its ramp is **identified** when the report gives its direction
of travel, on or off, and its cross street, and exactly one Caltrans ramp (district ramp ADT files, aadt.py) within
RAMP_MI of the crash's derived postmile (#248) on the same route and county fits all three. When 2 or more fit, the
engineer picks one (approved once); otherwise the crash gets no ramp rate, and the reason says why. Code only: no
guessing between ramps.

- Direction: from the ramp road ("I-405 S/B OFF RAMP", "ONRAMP TO I-680S"), else from a road that names a route;
  never from a local street's own direction ("RALSTON AVENUE NORTHBOUND").
- On or off: ON RAMP / ONRAMP / ON FROM, OFF RAMP / OFFRAMP / OFF TO; "ON/OFF" says neither.
- Cross street: the street named in the ramp road ("TO VERMONT AVE OFF-RAMP"), else the other road when it isn't
  only a route. Words match exactly, or as a prefix of 4+ letters (HILL / HILLS); generic words (EL, SAN, NORTH...)
  never match on their own; a number counts only after a street word (AVE 200 = RD 200).
- Caltrans descriptions: "SB OFF TO VERMONT AVE", "099/NB ON FR BELLEVUE RD", "NBOFF TRAVER/MERRITT DR", "RIVER RD
  OC SB ON RAMP", "NORWOOD TO WB-80" (on), "WB-80 TO NORWOOD" (off). Ramp segments ("SEG ...") and freeway
  connectors ("CONN") aren't ramps to a street and are left out.
"""

from __future__ import annotations

import re

from .aadt import count_year

RAMP_MI = 0.3
RAMP = re.compile(r"\b(?:ON|OFF)?[\s-]*RAMPS?\b|\bON[\s-]?RAMP\b|\bOFF[\s-]?RAMP\b|ONRAMP|OFFRAMP|\bONR\b|\bOFR\b")
ROUTE_REF = re.compile(r"\b(?:STATE ROUTE|INTERSTATE|HIGHWAY|ROUTE|HWY|RTE|RT|SR|CA|US|I)\.?[\s-]*0*(\d{1,3})([NSEW])?\b")
DIR = re.compile(r"(?:\b|(?<=\d)|(?<=/))(?:([NSEW])\s*/\s*B|([NSEW])B(?=\b|ON|OFF)|(NORTH|SOUTH|EAST|WEST)\s*BOUND)")
ON = re.compile(r"\bON[\s-]?RAMP|ONRAMP|\bONR\b|\bON\s+(?:FR|FROM)\b|\b[NSEW]B\s*ON\b|\b[NSEW]BON\b|\bON\b")
OFF = re.compile(r"\bOFF[\s-]?RAMP|OFFRAMP|\bOFR\b|\bOFF\s*TO\b|OFFTO|\b[NSEW]BOFF\b|\bOFF\b")
STOP = {"RAMP", "RAMPS", "ON", "OFF", "TO", "FR", "FROM", "NB", "SB", "EB", "WB", "N", "S", "E", "W", "B", "SEG", "OC",
        "UC", "OFFRAMP", "ONRAMP", "ONR", "OFR", "OFFTO", "NBON", "SBON", "EBON", "WBON", "NBOFF", "SBOFF", "EBOFF",
        "WBOFF", "NORTHBOUND", "SOUTHBOUND", "EASTBOUND", "WESTBOUND", "FWY", "FREEWAY", "AND", "THE", "OF", "JCT", "O",
        "C", "OVERCROSSING", "UNDERCROSSING", "OVER", "UNDER", "CROSSING", "TRANSITION", "LOOP", "DIAG", "DIAGONAL"}
STREET = {"AVE", "AV", "AVENUE", "BLVD", "BL", "BOULEVARD", "ST", "STREET", "RD", "ROAD", "DR", "DRIVE", "WY", "WAY",
          "LN", "LANE", "PKWY", "PKY", "PARKWAY", "CT", "PL", "HY", "EXPWY", "EXPRESSWAY", "CIR", "TRL", "TRAIL"}
GENERIC = {"EL", "LA", "LAS", "LOS", "SAN", "SANTA", "DEL", "DE", "NORTH", "SOUTH", "EAST", "WEST", "OLD", "NEW",
           "MOUNT", "MT", "LAKE", "VALLEY"}


def _dir(text: str) -> str | None:
    m = DIR.search(text)
    if m:
        return m.group(1) or m.group(2) or m.group(3)[0]
    m = next((m for m in ROUTE_REF.finditer(text) if m.group(2)), None)       # "I-680S", "SR 4 E"
    return m.group(2) if m else None


def _on_off(text: str) -> str | None:
    if re.search(r"\bON\s*/\s*OFF\b|\bOFF\s*/\s*ON\b|\bOFF AND ON\b|\bON AND OFF\b", text):
        return None
    on, off = bool(ON.search(text)), bool(OFF.search(text))
    return "ON" if on and not off else "OFF" if off and not on else None


def _words(text: str) -> list[str]:
    toks = re.findall(r"[A-Z0-9]+", ROUTE_REF.sub(" ", text))
    out = []
    for i, t in enumerate(toks):
        if t in STOP or t in STREET:
            continue
        if t.isdigit() and not (i and toks[i - 1] in STREET):                 # "AVE 200" yes, "(4)" no
            continue
        out.append(t)
    return out


def report(c: dict) -> dict | None:
    """What a crash report says about its ramp; None when it doesn't name one."""
    p, s = str(c.get("primary_road") or "").upper(), str(c.get("secondary_road") or "").upper()
    if RAMP.search(p):
        ramp, other = p, s
    elif RAMP.search(s):
        ramp, other = s, p
    else:
        return None
    d = _dir(ramp) or (_dir(other) if ROUTE_REF.search(other) else None)
    cross = _words(ramp) or (_words(other) if _words(other) else [])
    return {"dir": d, "on_off": _on_off(ramp), "cross": cross}


def describe(desc: str) -> dict:
    """Direction, on or off and street words of a Caltrans ramp description."""
    t = " ".join(str(desc or "").upper().split())
    d = _dir(t)
    oo = _on_off(t)
    m = re.match(r"^(.+?)\s+TO\s+(.+)$", t)
    if oo is None and m:                                                       # "NORWOOD TO WB-80" / "WB-80 TO NORWOOD"
        a, b = m.groups()
        oo = "ON" if ROUTE_REF.search(b) or DIR.search(b) and re.search(r"\d", b) else \
             "OFF" if ROUTE_REF.search(a) or DIR.search(a) and re.search(r"\d", a) else None
        if d is None:
            d = _dir(b if oo == "ON" else a)
    return {"dir": d, "on_off": oo, "words": set(_words(t))}


def _same_word(a: str, b: str) -> bool:
    return a == b or (len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)))


def _cross_fits(cross: list[str], words: set[str]) -> bool:
    key = [w for w in cross if w not in GENERIC and (len(w) >= 3 or w.isdigit())]
    return bool(key) and any(_same_word(w, v) for w in key for v in words)


def candidates(c: dict, cache) -> tuple[list[dict], list[dict]]:
    """(the Caltrans ramps within RAMP_MI, those that fit the report)."""
    p, r = c.get("postmile"), report(c)
    near = [x for x in cache.ramps_near(p["route"], p["county"], p["pm"], RAMP_MI, p.get("route_suffix") or "")
            if not x["description"].startswith("SEG") and "CONN" not in x["description"].split()]
    fit = []
    for x in near:
        d = describe(x["description"])
        if d["dir"] == r["dir"] and d["on_off"] == r["on_off"] and _cross_fits(r["cross"], d["words"]):
            fit.append(x)
    return near, fit


def identify(c: dict, cache, picks: dict | None = None) -> dict | None:
    """{"status": "identified" | "pick" | "none", "ramp", "candidates", "why", "picked", "year"} for a ramp crash
    with a postmile; None for any other crash."""
    p, r = c.get("postmile"), report(c)
    if not p or r is None or cache is None:
        return None
    year = count_year(c.get("reported_at") or c.get("date"))
    base = {"crash_id": c.get("crash_id"), "year": year, "report": r, "picked": False}
    missing = [w for w, ok in (("direction", r["dir"]), ("on or off", r["on_off"]), ("cross street", r["cross"]))
               if not ok]
    if missing:
        why = "no cross street" if missing == ["cross street"] else \
              "on or off not stated" if missing == ["on or off"] else f"no {' or '.join(missing)} in the report"
        return {**base, "status": "none", "why": why}
    near, fit = candidates(c, cache)
    if not near:
        return {**base, "status": "none", "why": f"no Caltrans ramp within {RAMP_MI:g} mi"}
    pick = (picks or {}).get(c.get("crash_id"))
    chosen = next((x for x in fit if x["id"] == pick), None)
    if chosen:
        return {**base, "status": "identified", "ramp": chosen, "picked": True}
    if len(fit) == 1:
        return {**base, "status": "identified", "ramp": fit[0]}
    if fit:
        return {**base, "status": "pick", "candidates": fit}
    return {**base, "status": "none", "why": "no Caltrans ramp fits"}
