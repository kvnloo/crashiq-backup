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
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import profile as profile_mod
from .assign import for_study

CREDITS = ("Crash data: CCRS, California Highway Patrol (data.ca.gov, public domain). "
           "Map data © OpenStreetMap contributors (ODbL).")
NO_AI = ("This report has no AI narrative. Findings are written by code from the over-representation screen (table T12, HSM excess-proportion test) and appear only after you accept them.")


def gather(db, sid: str) -> dict:
    study, net, pull, a = for_study(db, sid)
    from .findings import check_stored        # local import: findings imports profile, which export also uses
    accepted = [f for f in check_stored(db, sid) if f["status"] == "accepted"]
    return {"study": study, "network": net, "profile": profile_mod.build(study, net, pull, a),
            "findings": [f for f in accepted if not f["stale"]],
            "stale_findings": sum(f["stale"] for f in accepted),
            "assignment": {"counts": a["counts"], "excluded_by_rule": a["excluded_by_rule"]},
            "pulled_at": pull.get("pulled_at"),
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}


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
        sh.append([])
        sh.append(["Location sources"] + [f"{k}: {v}" for k, v in t["provenance"].items()])
        sh.column_dimensions["A"].width = 22
        sh.column_dimensions["B"].width = 44
        for i in range(3, len(t["columns"]) + 3):
            sh.column_dimensions[get_column_letter(i)].width = 12
        sh.freeze_panes = "C3"
        for row in sh.iter_rows(min_row=3):
            for c in row[2:]:
                c.alignment = Alignment(horizontal="right")
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
             "freeway": "on a freeway or ramp (CHP IsFreeway)", "no_segment": "not on a study segment"}


def methodology(d: dict) -> str:
    """Plain statement of how the numbers were made, printed with every PDF (reviewers ask for it)."""
    s, asg = d["study"], d.get("assignment") or {}
    ex = asg.get("excluded_by_rule") or {}
    excl = "; ".join(f"{n} {RULE_TEXT.get(k, k)}" for k, n in sorted(ex.items())) or "none"
    unplaced = (asg.get("counts") or {}).get("unmatched", 0)
    return (f"Crash data: CCRS (California Highway Patrol), {s['from_year']}–{s['to_year']}"
            + (f", pulled {d['pulled_at'][:10]}" if d.get("pulled_at") else "") + ". "
            f"A crash is assigned to the nearest study intersection within {s['radius_ft']:g} ft; otherwise to the "
            f"corridor segment when within {s['buffer_ft']:g} ft of the corridor line. Excluded: {excl}. "
            f"{unplaced} crash{'es' if unplaced != 1 else ''} had no usable coordinates and {'are' if unplaced != 1 else 'is'} "
            "not placed. Severity: each crash counted once at its most severe outcome (KABCO). Rates appear only where "
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

    def src(tid):
        return Paragraph(f"Source: table {tid}, computed from the CCRS records listed in the appendix workbook.", small)

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
    story += [KeepTogether([Paragraph("Severity (each crash counted once)", h2),
                            table([["Severity", "Crashes", "Share %"]] + [[r["label"], _fmt(r["values"]["crashes"]),
                                   _fmt(r["values"]["share_pct"], 1)] for r in t3["rows"]], cols(W - 2.4 * inch, 2), (1, 2)),
                            src("T3")])]
    for tid, title, limit, label in (("T4", "Collision type", None, "Type"),
                                     ("T5", "Primary collision factor (top 10)", 10, "Factor"),
                                     ("T6", "Lighting", None, "Lighting")):
        t = _t(p, tid)
        rows = t["rows"][:limit] if limit else t["rows"]
        story += [KeepTogether([Paragraph(title, h2), table(
            [[label, "Crashes", "Injury", "KSI", "Share %"]] + [[Paragraph(r["label"], cellp), _fmt(r["values"]["crashes"]),
                                                              _fmt(r["values"]["injury_crashes"]), _fmt(r["values"]["ksi_crashes"]),
                                                              _fmt(r["values"]["share_pct"], 1)] for r in rows],
            cols(W - 3.6 * inch, 4), (1, 2, 3, 4)), src(tid)])]
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
        story.append(Paragraph(f"{d['stale_findings']} accepted finding(s) no longer match the data after a study "
                               "change and are left out until reviewed again.", small))
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
    d = gather(request.app.state.db, sid)
    return Response(to_xlsx(d), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{_fname(d["study"], "xlsx")}"'})


@router.get("/studies/{sid}/export.pdf")
def export_pdf(sid: str, request: Request):
    d = gather(request.app.state.db, sid)
    return Response(to_pdf(d), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{_fname(d["study"], "pdf")}"'})


