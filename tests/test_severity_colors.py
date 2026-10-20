"""#108: one severity ramp. The backend constants, the frontend module and the CSS tokens must be identical, and no
other frontend file may hard-code a severity colour (old or new)."""

from __future__ import annotations

import io
import re
from pathlib import Path

from crashiq.severity import COLORS

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "frontend" / "src"


def test_frontend_module_mirrors_the_backend():
    js = (FRONT / "lib" / "severity.js").read_text()
    got = dict(re.findall(r"(\w): '(#[0-9a-fA-F]{6})'", js.split("SEVERITY_LABEL")[0]))
    assert {k: v.lower() for k, v in got.items()} == COLORS


def test_css_tokens_mirror_the_backend():
    css = (FRONT / "styles" / "app.css").read_text()
    got = {k.upper(): v.lower() for k, v in re.findall(r"--sev-([kabcuo]):\s*(#[0-9a-fA-F]{6})", css)}
    assert got == COLORS


def test_no_other_frontend_file_hard_codes_a_severity_colour():
    # Views use lib/severity.js or the --sev-* tokens. Two checks: the ramp's colours appear nowhere else (U's grey is
    # the theme's muted grey, so it's not banned), and no file builds its own severity map from literal hex values
    # (the old SEV = { K: '#FF5A4E', ... } pattern). Theme colours that merely share an old hex (traffic lamps, LOS)
    # are not severity and stay.
    allowed = {FRONT / "lib" / "severity.js", FRONT / "styles" / "app.css"}
    ramp = {v for k, v in COLORS.items() if k != "U"}
    sev_map = re.compile(r"\b[KAO]\s*:\s*['\"]#[0-9a-fA-F]{6}")
    hits = []
    for f in FRONT.rglob("*"):
        if f.suffix in {".js", ".jsx", ".css"} and f not in allowed and "__fixtures__" not in f.parts:
            text = f.read_text()
            hits += [f"{f.relative_to(ROOT)}: {h}" for h in ramp if h in text.lower()]
            hits += [f"{f.relative_to(ROOT)}: severity map {m}" for m in sev_map.findall(text)]
    assert not hits, hits


def test_exports_use_the_ramp(client):
    import json

    from openpyxl import load_workbook

    from crashiq import export
    from crashiq.sources.fake_ckan import FakeCkan
    from conftest import FIXTURES
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(json.loads((FIXTURES / "ckan_crenshaw.json").read_text()))
    sid = client.post("/api/studies", json={"name": "Sev", "mode": "profile"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": [[33.8953, -118.32662], [33.9040, -118.32662],
                                                              [33.9123, -118.32662]]})
    client.post(f"/api/studies/{sid}/crashes/pull")
    d = export.gather(client.app.state.db, sid)
    wb = load_workbook(io.BytesIO(export.to_xlsx(d)))
    sh = next(s for s in wb.worksheets if s.title.startswith("T3"))
    fills = {sh.cell(row=r, column=1).value: sh.cell(row=r, column=1).fill.fgColor.rgb[-6:].lower()
             for r in range(3, 3 + 6)}
    assert fills == {k: v.lstrip("#") for k, v in COLORS.items()}
    assert export.to_pdf(d)[:4] == b"%PDF"            # the severity table with its colour swatches renders
