"""C13 export (v1: crash profile / TIS mode): Excel workbook and PDF built only from the C6 profile response.
No number is computed here; values are copied from the cited tables (T1…T11) and their cells."""

from __future__ import annotations

import io
from xml.sax.saxutils import escape
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
import math

from reportlab.graphics.shapes import Circle, Drawing, Group, PolyLine, Polygon, Rect, String
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import locate
from . import union as union_mod
from . import profile as profile_mod
from .severity import COLORS as SEV_COLORS
from .assign import for_study

CREDITS = ("Crash data: CCRS, California Highway Patrol (data.ca.gov, public domain). "
           "Map data © OpenStreetMap contributors (ODbL). Fatal crash locations marked 'fars': FARS, NHTSA "
           "(public domain).")
NO_AI = ("This report has no AI narrative. Findings are written by code from the over-representation screen (table T12, HSM excess-proportion test) and appear only after you accept them.")


def _roads(c: dict) -> str:
    """The report's two road fields, then where a house-address crash happened (#397: "in front of 440 W MANCHESTER
    BLVD")."""
    roads = f"{c.get('primary_road') or ''} / {c.get('secondary_road') or ''}"
    return f"{roads} ({c['location_label']})" if c.get("location_label") else roads


def stale_text(n: int) -> str:
    """Singular or plural by count (#266)."""
    return (f"{n} accepted finding{'' if n == 1 else 's'} no longer match{'es' if n == 1 else ''} the data after a "
            f"study change and {'is' if n == 1 else 'are'} left out until reviewed again.")


def _postmiles(pull: dict, a: dict, pm) -> list[dict]:
    """Counted crashes on a state route with their derived Caltrans postmile (#248)."""
    if pm is None:
        return []
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    out = []
    for x in a["assignments"]:
        if x["kind"] not in ("intersection", "segment"):
            continue
        c = by_id[x["crash_id"]]
        p = pm.for_crash(c)
        if p:
            out.append({"crash_id": c["crash_id"], "roads": _roads(c),
                        "date": c.get("date"), "postmile": p["label"], "align": p["align"], "direction": p["direction"],
                        "distance_ft": round(p["distance_m"] * 3.28084), "assigned_to": x["location_id"]})
    return out


def gather(db, sid: str, postmiles=None, aadt_cache=None) -> dict:
    study, net, pull, a = for_study(db, sid)
    net = profile_mod.with_shs(net, pull, postmiles, aadt_cache)        # state-highway rates (#287)
    from .findings import check_stored        # local import: findings imports profile, which export also uses
    accepted = [f for f in check_stored(db, sid) if f["status"] == "accepted"]
    return {"study": study, "network": net, "profile": profile_mod.build(study, net, pull, a),
            "findings": [f for f in accepted if not f["stale"]],
            "stale_findings": sum(f["stale"] for f in accepted),
            "assignment": {"counts": a["counts"], "excluded_by_rule": a["excluded_by_rule"],
                           "unmatched_by_rule": a.get("unmatched_by_rule", {})},
            "pulled_at": pull.get("pulled_at"),
            "decisions": _decisions(db, sid, pull, a), "diagrams": _diagrams(net, pull, a), "fars": _fars_placed(pull, a),
            "postmiles": _postmiles(pull, a, postmiles),
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}


def _decisions(db, sid: str, pull: dict, a: dict) -> list[dict]:
    """The engineer's review-list decisions (#97), listed in the export: what was placed or excluded by hand."""
    from .review import decisions
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    kind = {x["crash_id"]: (x["kind"], x["location_id"]) for x in a["assignments"]}
    out = []
    for cid, d in sorted(decisions(db, sid).items()):
        c = by_id.get(cid)
        if c is None:
            continue
        k, loc = kind.get(cid, (None, None))
        out.append({"crash_id": cid, "roads": _roads(c),
                    "date": c.get("date"), "action": d["action"], "method": d["method"], "reason": d["reason"],
                    "fatal": c.get("severity") == "K" or (c.get("killed") or 0) > 0, "source": d.get("source"),
                    "assigned_to": loc or k, "applied": c.get("stale_decision") is None,
                    "decided_at": d["decided_at"]})
    return out


def _fars_placed(pull: dict, a: dict) -> list[dict]:
    """Fatal crashes located by their linked FARS point (#174), with the FARS case, for the export."""
    loc = {x["crash_id"]: x["location_id"] or x["kind"] for x in a["assignments"]}
    return [{"crash_id": c["crash_id"], "roads": _roads(c),
             "date": c.get("date"), "fars_case": c.get("fars_case"), "lat": c.get("lat"), "lon": c.get("lon"),
             "replaced_gps": c.get("gps_replaced"), "assigned_to": loc.get(c["crash_id"])}
            for c in pull["crashes"] if c.get("location_source") == "fars"]


def _diagrams(net: dict, pull: dict, a: dict) -> list[dict]:
    """One collision diagram per study intersection with crashes, in corridor order (#106, N10)."""
    from . import diagram as diagram_mod
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    at: dict[str, list] = {}
    for x in a["assignments"]:
        if x["kind"] == "intersection":
            at.setdefault(x["location_id"], []).append(by_id[x["crash_id"]])
    return [{"name": it["name"], "diagram": diagram_mod.build(net, it, at[it["id"]])}
            for it in sorted(net["intersections"], key=lambda i: i["station_ft"]) if it.get("is_study") and at.get(it["id"])]


_DIAG_COLOR = {"ink": "#22282E", "arm": "#969696", "muted": "#57636F", "paper": "#FFFFFF",
               **{f"sev_{k.lower()}": v for k, v in SEV_COLORS.items()}}


def diagram_drawing(d: dict, size: float) -> Drawing:
    """The diagram's drawing steps (the same the app draws as SVG) as a ReportLab drawing, size x size points."""
    W, H = d["width"], d["height"]
    k = size / W
    col = lambda name: colors.HexColor(_DIAG_COLOR.get(name, name))      # noqa: E731
    pt = lambda x, y: (x * k, (H - y) * k)                               # noqa: E731 - SVG is y-down, PDF y-up
    g = Group()
    for s in d["steps"]:
        op = s["op"]
        if op == "rect_cell":
            g.add(Rect(0, 0, W * k, H * k, fillColor=col("paper"), strokeColor=col("ink"), strokeWidth=0.6))
        elif op == "line":
            pts = [c for p in s["pts"] for c in pt(*p)]
            g.add(PolyLine(pts, strokeColor=col(s["color"]), strokeWidth=s["w"] * k, strokeLineCap=1, strokeLineJoin=1,
                           strokeDashArray=[1.5 * s["w"] * k, 3 * s["w"] * k] if s["dash"] else None))
        elif op == "head":
            a, sz = math.radians(s["ang"]), s.get("size", 1)
            tri = [(0, -4), (3.4, 3), (-3.4, 3)]
            pts = [c for x, y in tri for c in pt(s["x"] + sz * (x * math.cos(a) - y * math.sin(a)),
                                                  s["y"] + sz * (x * math.sin(a) + y * math.cos(a)))]
            g.add(Polygon(pts, fillColor=col(s["color"]) if s["filled"] else col("paper"), strokeColor=col(s["color"]),
                          strokeWidth=1.3 * k, strokeLineJoin=1))
        elif op == "circle":
            x, y = pt(s["x"], s["y"])
            g.add(Circle(x, y, s["r"] * k, fillColor=col(s["fill"]), strokeColor=col(s["stroke"]), strokeWidth=s["w"] * k))
        elif op == "poly":
            g.add(Polygon([c for p in s["pts"] for c in pt(*p)], fillColor=col(s["fill"]), strokeColor=col(s["stroke"]),
                          strokeWidth=s["w"] * k))
        elif op == "text":
            x, y = pt(s["x"], s["y"])
            anchor = {"start": "start", "end": "end"}.get(s["anchor"], "middle")
            t = String(0, 0, s["t"], fontSize=s["size"] * k, fillColor=col(s["color"]), textAnchor=anchor,
                       fontName="Helvetica-Bold" if s.get("bold") else "Helvetica")
            tg = Group(t)
            tg.translate(x, y)
            if s.get("rot"):
                tg.rotate(-s["rot"])                      # SVG rotates clockwise on a y-down page
            g.add(tg)
        elif op == "north":
            x, y = s["x"], s["y"]
            g.add(Polygon([c for p in ((x, y - 18), (x + 7, y + 4), (x, y - 2), (x - 7, y + 4)) for c in pt(*p)],
                          fillColor=col("ink"), strokeColor=col("ink"), strokeWidth=0.1))
            tx, ty = pt(x, y + 18)
            g.add(String(tx, ty, "N", fontSize=11 * k, textAnchor="middle", fillColor=col("ink"), fontName="Helvetica-Bold"))
    dr = Drawing(size, size)
    dr.add(g)
    return dr


def _t(p, tid):
    return next(t for t in p["tables"] if t["id"] == tid)


def _fname(study, ext):
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in study["name"]).strip("_") or "study"
    return f"CrashIQ_{safe}_{study['from_year']}-{study['to_year']}.{ext}"


# -- Excel -----------------------------------------------------------------------------------------------
def to_xlsx(d: dict) -> bytes:
    s, net, p = d["study"], d["network"], d["profile"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Study"
    bold = Font(bold=True)
    rows = [("CrashIQ crash profile", ""), ("Project", s["name"]), ("Study type", s["mode_label"]),
            ("Crash history", f"{s['from_year']}–{s['to_year']}"), ("Corridor", net.get("corridor_name") or ""),
            ("Corridor length (mi)", profile_mod.cell(p["tables"], "T1/length_mi/value")),
            ("Influence radius (ft)", s["radius_ft"]), ("Corridor buffer (ft)", s["buffer_ft"]),
            ("Generated", d["generated"]), ("Data pulled", p["pulled_at"]), ("", ""), ("Caveats", "")]
    rows += [("", c["text"]) for c in p["caveats"]] or [("", "None")]
    rows += [("", ""), ("Note", NO_AI), ("Sources", CREDITS),
             ("Tables", "Each sheet is one cited table (T1…T12). Cell = sheet / row key / column.")]
    for r in rows:
        ws.append(list(r))
    ws["A1"].font = Font(bold=True, size=14)
    for row in ws.iter_rows(min_row=2, max_col=1):
        row[0].font = bold
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 90
    head = PatternFill("solid", fgColor="22282E")
    for t in p["tables"]:
        sh = wb.create_sheet(f"{t['id']} {t['title']}"[:31].replace("/", "-").replace(":", "-"))
        sh.append([f"{t['id']} · {t['title']}"])
        sh["A1"].font = Font(bold=True, size=12)
        sh.append(["Row key", "Label"] + [c["label"] for c in t["columns"]])
        for cell in sh[2]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = head
        for r in t["rows"]:
            sh.append([r["key"], r["label"]] + [r["values"].get(c["key"]) for c in t["columns"]])
            if t["id"].startswith("T3") and r["key"] in SEV_COLORS:     # the app's severity ramp (#108)
                sh.cell(row=sh.max_row, column=1).fill = PatternFill("solid", fgColor=SEV_COLORS[r["key"]].lstrip("#"))
        sh.append([])
        sh.append(["Location sources"] + [f"{k}: {v}" for k, v in t["provenance"].items()])
        if t.get("note"):                       # a missing CCRS Parties / IWP year (#188)
            sh.append(["Note", t["note"]])
        if t.get("source_note"):                # a reference table a column is priced from (#273)
            sh.append(["Source", t["source_note"]])
            sh.cell(row=sh.max_row, column=1).font = Font(bold=True, color="C4261B")
        sh.column_dimensions["A"].width = 22
        sh.column_dimensions["B"].width = 44
        for i in range(3, len(t["columns"]) + 3):
            sh.column_dimensions[get_column_letter(i)].width = 12
        sh.freeze_panes = "C3"
        for row in sh.iter_rows(min_row=3):
            for c in row[2:]:
                c.alignment = Alignment(horizontal="right")
    if d.get("decisions"):
        sh = wb.create_sheet("Review decisions")
        sh.append(["Placed or excluded by the engineer on the review list (provenance 'user'). Every count is still "
                   "computed by code from these locations."])
        sh["A1"].font = Font(bold=True, size=12)
        sh.append(["Collision Id", "Roads (as reported)", "Date", "Fatal", "Action", "How", "Reason", "Source (fatal: required)",
                   "Assigned to", "Applied", "Decided"])
        for cell in sh[2]:
            cell.font = Font(bold=True)
        for r in d["decisions"]:
            sh.append([r["crash_id"], r["roads"], r["date"], "yes" if r["fatal"] else "", r["action"], r["method"] or "",
                       r["reason"] or "", r["source"] or "", r["assigned_to"] or "",
                       "yes" if r["applied"] else "no (report revised; re-review)", r["decided_at"]])
        sh.column_dimensions["B"].width = 44
    if d.get("fars"):
        sh = wb.create_sheet("FARS-placed fatal crashes")
        sh.append(["Fatal crashes with no usable location in CCRS, placed at their linked FARS point (NHTSA, public "
                   "domain) because it fits the streets the report names (provenance 'fars'). FARS case = year-ST_CASE."])
        sh["A1"].font = Font(bold=True, size=12)
        sh.append(["Collision Id", "Roads (as reported)", "Date", "FARS case", "Latitude", "Longitude",
                   "CCRS GPS replaced", "Assigned to"])
        for cell in sh[2]:
            cell.font = Font(bold=True)
        for r in d["fars"]:
            sh.append([r["crash_id"], r["roads"], r["date"], r["fars_case"], r["lat"], r["lon"],
                       ", ".join(str(v) for v in r["replaced_gps"]) if r["replaced_gps"] else "", r["assigned_to"] or ""])
        sh.column_dimensions["B"].width = 44
    if d.get("postmiles"):
        sh = wb.create_sheet("State-highway postmiles")
        sh.append(["Caltrans postmile of each counted crash on a state route, derived from where CrashIQ placed it "
                   "(public SHN Postmiles Tenth layer, interpolated between its 0.1-mile points; not from CHP)."])
        sh["A1"].font = Font(bold=True, size=12)
        sh.append(["Collision Id", "Roads (as reported)", "Date", "Postmile (derived)", "Side", "Direction",
                   "Distance to the route (ft)", "Assigned to"])
        for cell in sh[2]:
            cell.font = Font(bold=True)
        for r in d["postmiles"]:
            sh.append([r["crash_id"], r["roads"], r["date"], r["postmile"], r["align"], r["direction"],
                       r["distance_ft"], r["assigned_to"] or ""])
        sh.column_dimensions["B"].width = 44
        sh.column_dimensions["D"].width = 22
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# -- PDF -------------------------------------------------------------------------------------------------
def _fmt(v, d=None):
    if v is None:
        return "—"
    if isinstance(v, float) and d is not None:
        return f"{v:,.{d}f}"
    return f"{v:,}" if isinstance(v, (int, float)) else str(v)


RULE_TEXT = {"outside_buffer": "outside the corridor buffer", "outside_study_limits": "beyond the study limits",
             "fars_off_corridor": "fatal crashes FARS places elsewhere on the report's roads, off the study corridor",
             "freeway": "on a freeway or ramp (CHP IsFreeway)", "no_segment": "not on a study segment",
             "cross_street_not_on_corridor": "at a cross street that is not one of the corridor's intersections",
             "grade_separated_crossing": "on a road passing over or under the corridor",
             "not_on_freeway": "not on the freeway (CHP IsFreeway false)", "ramp": "on a freeway ramp",
             "not_on_corridor_street": "on another street (the report names neither the corridor nor the cross street)",
             "no_cross_street": "no cross street in the report (not stated), so its place on the corridor is unknown",
             "private_property": "on private property",
             "crossing": "at a railway or a trail or path, not one of the corridor's intersections (on the review list with "
                         "the crossing as the suggestion, until that placement is approved, or with why there's no one "
                         "crossing)",
             "mile_marker": "a mile marker instead of a cross street (on the review list with its Caltrans postmile point "
                            "as the suggestion, until that placement is approved)",
             "house_address": "a house address instead of a cross street, with no address point that places it (on "
                              "the review list with a county address point or the Census TIGER address-range point "
                              "as the suggestion)",
             "user_excluded": "excluded by the engineer on the review list (reason in the Review decisions sheet)"}


def _address_credits(d: dict) -> str:
    """The address lists this study's house-address placements came from, in their own words (#408)."""
    cav = next((c for c in (d.get("profile") or {}).get("caveats", []) if c["key"] == "address_nad"), None)
    if not cav or not cav.get("sources"):
        return ""
    return "Address points used in this study: " + ", ".join(
        f"{s} ({n} crash{'' if n == 1 else 'es'})" for s, n in cav["sources"].items()) + ". "


def methodology(d: dict) -> str:
    """Plain statement of how the numbers were made, printed with every PDF (reviewers ask for it)."""
    s, asg = d["study"], d.get("assignment") or {}
    ex = asg.get("excluded_by_rule") or {}
    excl = "; ".join(f"{n} {RULE_TEXT.get(k, k)}" for k, n in sorted(ex.items())) or "none"
    unplaced = (asg.get("counts") or {}).get("unmatched", 0)
    ncs = (asg.get("unmatched_by_rule") or {}).get("no_cross_street", 0)
    return (f"Crash data: CCRS (California Highway Patrol), {s['from_year']}–{s['to_year']}"
            + (f", pulled {d['pulled_at'][:10]}" if d.get("pulled_at") else "") + ". "
            f"A crash is assigned to the nearest study intersection within {s['radius_ft']:g} ft; otherwise to the "
            f"corridor segment when within {s['buffer_ft']:g} ft of the corridor line (equal distances to two "
            "intersections go to the one nearer the corridor's start). A GPS crash must name the corridor street, or "
            "at an intersection its cross street. A report without GPS counts only if it was filed in a city the "
            "corridor enters (OpenStreetMap city limits along the line and buffer), or in the unincorporated county "
            "where the corridor leaves city limits. Only intersections the corridor "
            "meets at grade count; a road passing over or under it (an overcrossing, undercrossing or freeway, found "
            "from OpenStreetMap where the roads cross without a shared node) is not an intersection, and crashes on "
            "that road are excluded. A report without GPS is placed from its two street names on OpenStreetMap: where "
            "both names match exactly, or where the two streets can meet at only one place when a direction or suffix "
            "the report leaves out may differ (AVENUE J & 20TH ST W can only be West Avenue J & 20th Street West); a "
            "direction the report writes must match. A city's own spelling of a street, approved entry by entry, is read "
            "as the map street's name in that city only. A street name one or two letters off a single map street (no "
            "other street as close, no change of numbers, and the corrected pair meeting at only one place) is suggested "
            "on the review list until its accuracy is measured and approved. Street pairs that meet in more than one "
            "place, and looser matches, go to the review list for the engineer. Police GPS at the intersection the report names, when the "
            "report states a distance and direction from it, is moved by that distance along the named road. GPS on a "
            "default point (one exact point shared by 10 or more reports naming 5 or more different street pairs, "
            "most of which it doesn't fit), or written with 2 decimals or fewer (both coordinates, or one where the point doesn't "
            "fit the report's streets), is not used; those reports are placed "
            "by their street names. "
            + ("The street network is OpenStreetMap joined with the US Census TIGER/Line roads: a TIGER road that runs "
               "along an OpenStreetMap street adds its names to it, and one OpenStreetMap lacks is added; a placement "
               "that needs a name or road only TIGER/Line has is marked, and one that needs a road only TIGER/Line has "
               "goes to the review list as a suggestion. " if union_mod.enabled() else "The street network is "
               "OpenStreetMap. ")
            + "A freeway crash with no usable GPS is placed approximately (usually within 0.5 mi: about 9 in 10 tested crashes) from the "
            "report: where "
            "the reference street crosses the freeway, at the ramp terminal, or along the connector, plus the stated "
            "distance. Such crashes count on the corridor segments, never at an intersection, and intersection tables "
            "and collision diagrams leave them out. "
            + "A report that gives a house address instead of a cross street is placed approximately (usually within "
            "400 ft) at that address point in the crash's city, on the corridor in front of the address: from the USDOT "
            "National Address Database (NAD, release r24; 86% of tested crashes within 400 ft), or where NAD has none, "
            "from a county address list measured about as accurate (most accurate list first); such crashes also count "
            "on segments only. A less accurate county list only gives the review list a suggestion, and with no "
            "address point the crash goes to the review list with the Census TIGER address-range point as a "
            "suggestion. " + _address_credits(d)
            + ("A report that gives a mile marker on the state route instead of a cross street is placed at that "
               "Caltrans postmile (SHN Postmiles Tenth layer), plus any stated distance along the route. "
               if "postmile" in locate.configured_tiers() else "")
            + ("A report naming the corridor and a railway, trail or path is placed where the corridor crosses it, "
               "plus any stated distance along the path; two or more possible crossings go to the review list. "
               if {"crossing_rail", "crossing_path"} & locate.configured_tiers() else "")
            + f"Excluded: {excl}. "
            f"{unplaced} crash{'es' if unplaced != 1 else ''} had no usable coordinates and {'are' if unplaced != 1 else 'is'} "
            "not placed" + (f" ({ncs} of them name the corridor but give no cross street, so where on the corridor "
                            "is unknown; they are on the review list for the engineer to place)" if ncs else "")
            + ". Severity: each crash counted once at its most severe outcome (KABCO). Primary collision factor "
            "categories are the 24 SWITRS categories, from CHP's own Vehicle Code section table rebuilt from SWITRS "
            "records (a section is used only where 99% or more of its records agree); reports with no section, a "
            "description in words, or a section CHP did not categorize are listed as such. Rates appear only where "
            "AADT was entered" + (f" (estimated from peak-hour counts with K = {s.get('k_factor', 0.1):.0%})"
                                  if s.get("volume_basis") == "peak_hour" else "") + " (intersections per million entering vehicles from two-way AADT, a T counting half the "
            "minor road; segments per 100 million vehicle-miles). Where 3 or more similar locations have AADT, each "
            "location's rate is compared with its critical rate (HSM Ch. 4, 95% confidence) against the average of the "
            "corridor's own intersections or segments. This profile does not compare rates with statewide averages.")


def to_pdf(d: dict) -> bytes:
    s, net, p = d["study"], d["network"], d["profile"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch, title=f"{s['name']} crash profile",
                            author="CrashIQ")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], alignment=0, fontSize=20, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13, spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=colors.HexColor("#57636F"))
    cellp = ParagraphStyle("c", parent=body, fontSize=8.5, leading=10.5)
    dark, line = colors.HexColor("#22282E"), colors.HexColor("#D3D8DD")
    W = letter[0] - 1.4 * inch                      # every table spans the text width

    def cols(first, n):                             # label column + n equal number columns
        return [first] + [(W - first) / n] * n

    def table(data, widths, num_cols=()):
        t = Table(data, colWidths=widths, repeatRows=1)
        st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5), ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
              ("BACKGROUND", (0, 0), (-1, 0), dark), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
              ("LINEBELOW", (0, 1), (-1, -1), 0.4, line), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        for c in num_cols:
            st.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
        t.setStyle(TableStyle(st))
        return t

    notes = {t["id"]: t.get("note") for t in p["tables"]}

    def src(tid):
        note = f" Note: {escape(notes[tid])}" if notes.get(tid) else ""     # a missing CCRS Parties / IWP year (#188)
        return Paragraph(f"Source: table {tid}, computed from the CCRS records listed in the appendix workbook.{note}",
                         small)

    v = lambda a: profile_mod.cell(p["tables"], a)
    story = [Paragraph(f"{s['name']}: crash profile", h1),
             Paragraph(f"{net.get('corridor_name') or 'Corridor'} · {s['mode_label']} · crash history "
                       f"{s['from_year']}–{s['to_year']} · generated {d['generated']}", small), Spacer(1, 10)]
    kpis = [["Crashes", "KSI crashes", "Injury crashes", "Crashes per mile · year"],
            [_fmt(v(p["kpis"]["crashes"])), _fmt(v(p["kpis"]["ksi_crashes"])), _fmt(v(p["kpis"]["injury_crashes"])),
             _fmt(v(p["kpis"]["crashes_per_mi_yr"]))]]
    kt = Table(kpis, colWidths=[W / 4] * 4)
    kt.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica", 8), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#57636F")),
                            ("FONT", (0, 1), (-1, 1), "Helvetica-Bold", 18), ("BOX", (0, 0), (-1, -1), 0.6, line),
                            ("INNERGRID", (0, 0), (-1, -1), 0.6, line), ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [kt, src("T1")]

    t1 = _t(p, "T1")
    story += [Paragraph("Study summary", h2),
              table([["Measure", "Value"]] + [[r["label"], _fmt(r["values"]["value"])] for r in t1["rows"]],
                    cols(W - 1.4 * inch, 1), (1,)), src("T1")]
    t2 = _t(p, "T2")
    has_rate = any(r["values"]["rate"] is not None for r in t2["rows"])
    has_crit = any(r["values"].get("critical_rate") is not None for r in t2["rows"])
    head = (["Location", "Crashes", "Per yr", "KSI", "Injury", "Dark"] + (["Rate"] if has_rate else [])
            + (["Critical (95%)", "Over?"] if has_crit else []))
    data = [head] + [[Paragraph(r["label"], cellp), _fmt(r["values"]["crashes"]), _fmt(r["values"]["crashes_per_year"]),
                      _fmt(r["values"]["ksi_crashes"]), _fmt(r["values"]["injury_crashes"]),
                      _fmt(r["values"]["dark_crashes"])] + ([_fmt(r["values"]["rate"])] if has_rate else [])
                     + ([_fmt(r["values"].get("critical_rate")), r["values"].get("over_critical") or "—"] if has_crit else [])
                     for r in t2["rows"]]
    w = cols(2.6 * inch if has_crit else 3.1 * inch, len(head) - 1)
    story += [Paragraph("Locations (corridor order)", h2), table(data, w, range(1, len(head))), src("T2")]
    t3 = _t(p, "T3")
    sev_t = table([["", "Severity", "Crashes", "Share %"]] + [["", r["label"], _fmt(r["values"]["crashes"]),
                   _fmt(r["values"]["share_pct"], 1)] for r in t3["rows"]], [0.18 * inch, W - 2.58 * inch, 1.2 * inch, 1.2 * inch], (2, 3))
    sev_t.setStyle(TableStyle([("BACKGROUND", (0, i + 1), (0, i + 1), colors.HexColor(SEV_COLORS[r["key"]]))
                               for i, r in enumerate(t3["rows"]) if r["key"] in SEV_COLORS]))   # same ramp as the app
    story += [KeepTogether([Paragraph("Severity (each crash counted once)", h2), sev_t, src("T3")])]
    t14 = _t(p, "T14")                        # standard safety-section rows (#52)
    story += [KeepTogether([Paragraph("Hit and run, DUI and speed", h2),
                            table([["", "Crashes", "KSI", "Share %"]] + [[r["label"].strip(), _fmt(r["values"]["crashes"]),
                                   _fmt(r["values"]["ksi_crashes"]), _fmt(r["values"]["share_pct"], 1)] for r in t14["rows"]],
                                  cols(W - 3.3 * inch, 3), (1, 2, 3)), src("T14")])]
    t19 = _t(p, "T19")                        # pedestrians and bicyclists first (#136)
    story += [KeepTogether([Paragraph("Pedestrians and bicyclists", h2),
                            table([["", "Crashes", "KSI", "KSI % of group", "Share of KSI %"]]
                                  + [[r["label"], _fmt(r["values"]["crashes"]), _fmt(r["values"]["ksi_crashes"]),
                                      _fmt(r["values"]["ksi_pct"], 1), _fmt(r["values"]["share_of_ksi_pct"], 1)]
                                     for r in t19["rows"]], cols(W - 4.0 * inch, 4), (1, 2, 3, 4)), src("T19")])]
    for tid, title, limit, label in (("T20", "Pedestrian crashes by lighting", None, "Lighting"),
                                     ("T4", "Collision type", None, "Type"),
                                     ("T5", "Primary collision factor (top 10)", 10, "Factor"),
                                     ("T18", "Primary collision factor category", None, "Category"),
                                     ("T6", "Lighting", None, "Lighting")):
        t = _t(p, tid)
        rows = t["rows"][:limit] if limit else t["rows"]
        story += [KeepTogether([Paragraph(title, h2), table(
            [[label, "Crashes", "Injury", "KSI", "Share %"]] + [[Paragraph(r["label"], cellp), _fmt(r["values"]["crashes"]),
                                                              _fmt(r["values"]["injury_crashes"]), _fmt(r["values"]["ksi_crashes"]),
                                                              _fmt(r["values"]["share_pct"], 1)] for r in rows],
            cols(W - 3.6 * inch, 4), (1, 2, 3, 4)), src(tid)])]
    if d.get("diagrams"):                      # G. one collision diagram per study intersection (#106, N10)
        story += [Paragraph("Collision diagrams", h2),
                  Paragraph("One per study intersection with crashes. Symbols after HSM Ch. 5 / ITE; filled circle = "
                            "fatal, hollow circle = injury, crossbar = property damage only; hollow arrowhead = day, "
                            "filled = dark; identical crashes stacked (NCDOT). Numbers key to the list under each "
                            "diagram. Code = road surface + light (HSM): C dry, W wet, S snow/ice, O other; D daylight, "
                            "N dark without street lights, L dark with street lights.", small)]
        for x in d["diagrams"]:
            dg = x["diagram"]
            nd = sum((dg.get("not_drawn") or {}).values())
            rows = [["#", "Date", "Time", "Appr.", "Type", "Sev.", "Code"]] + [
                [r["n"], r["date"] or "", f"{r['hour']:02d}00" if r.get("hour") is not None else "—", r["approach"],
                 Paragraph(escape(r["type_label"]), cellp), r["severity"], r["code"]] for r in dg["crashes"]]
            lst = Table(rows, colWidths=[0.3 * inch, 0.8 * inch, 0.45 * inch, 0.45 * inch, 1.9 * inch, 0.35 * inch,
                                         0.45 * inch], repeatRows=1)
            lst.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7.5), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                     ("LINEBELOW", (0, 0), (-1, 0), 0.5, line), ("TOPPADDING", (0, 0), (-1, -1), 1),
                                     ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
            story += [KeepTogether([Paragraph(escape(x["name"]), body), diagram_drawing(dg, 4.6 * inch)]),
                      Paragraph(f"{len(dg['crashes'])} crashes" + (f"; {nd} not drawn (no direction of travel: no party "
                                                                    "data for their year in this pull), listed" if nd else ""),
                                small), lst, Spacer(1, 10)]
    story += [Paragraph("Method", h2), Paragraph(escape(methodology(d)), body)]
    story += [Paragraph("Caveats", h2)]
    story += [Paragraph("• " + c["text"], body) for c in p["caveats"]] or [Paragraph("None.", body)]
    story += [Paragraph("Findings", h2)]
    for i, f in enumerate(d.get("findings") or [], start=1):
        m = f.get("meta") or {}
        story.append(KeepTogether([
            Paragraph(f"<b>F{i}. {escape(f.get('title') or '')}</b>", body),
            Paragraph(escape(f["text"]), body),
            Paragraph(escape(f"Strength: {m.get('strength', '—')} · "
                             f"{'binomial confidence' if str(m.get('method', '')).startswith('Binomial') else 'P(share > reference)'} "
                             f"{m.get('probability', '—')} · compared with the {m.get('reference', 'corridor')} · "
                             f"{m.get('method', '')}. Pattern library: {f.get('pattern_ref') or 'no entry'}"
                             + (" (draft)" if m.get("library_status") == "draft" else "") + ". Source: table T12."), small),
            Spacer(1, 6)]))
    if not d.get("findings"):
        story.append(Paragraph("No findings accepted yet.", body))
    if p.get("screen_tests"):
        story.append(Paragraph(f"The screen ran {p['screen_tests']} location × crash-type tests at P ≥ 0.80, so a few patterns "
                               "can pass by chance. Treat findings as leads to verify in the field.", small))
    if d.get("stale_findings"):
        story.append(Paragraph(stale_text(d["stale_findings"]), small))
    story += [Paragraph(NO_AI, small), Spacer(1, 14), Paragraph(CREDITS, small)]
    from .references import cited_sources
    story += [Paragraph("References", h2),
              Paragraph("Each method in this report and the source it follows are listed in CrashIQ under "
                        "Methods &amp; references.", small)]
    story += [Paragraph(f"[{i}] {escape(r['publisher'])}, <i>{escape(r['title'])}</i>. {escape(r['url'])}", small)
              for i, r in enumerate(cited_sources(), start=1)]

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#57636F"))
        canvas.drawString(0.7 * inch, 0.45 * inch, f"CrashIQ · {s['name']} · {s['from_year']}–{s['to_year']}")
        canvas.drawRightString(letter[0] - 0.7 * inch, 0.45 * inch, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


router = APIRouter()


@router.get("/studies/{sid}/export.xlsx")
def export_xlsx(sid: str, request: Request):
    from .crashes import aadt_for, postmile_for
    d = gather(request.app.state.db, sid, postmile_for(request.app.state), aadt_for(request.app.state))
    return Response(to_xlsx(d), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{_fname(d["study"], "xlsx")}"'})


@router.get("/studies/{sid}/export.pdf")
def export_pdf(sid: str, request: Request):
    from .crashes import aadt_for, postmile_for
    d = gather(request.app.state.db, sid, postmile_for(request.app.state), aadt_for(request.app.state))
    return Response(to_pdf(d), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{_fname(d["study"], "pdf")}"'})


