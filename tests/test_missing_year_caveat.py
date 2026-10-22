"""#188: a year of CCRS Parties / IWP missing from the pull is disclosed on the profile, the affected tables and
the exports; with nothing missing, nothing is said."""

import io
import json
from datetime import datetime, timedelta, timezone

from openpyxl import load_workbook
from pypdf import PdfReader

from crashiq import crashes
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [[33.8953, -118.32662], [33.9123, -118.32662]]


def _study(client, drop=()):
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    d["package"]["resources"] = [r for r in d["package"]["resources"] if r["name"] not in drop]
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(d)
    sid = client.post("/api/studies", json={"name": "M", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    client.post(f"/api/studies/{sid}/crashes/pull")
    return sid


def test_missing_party_year_is_disclosed_everywhere(client):
    sid = _study(client, drop=("Parties_2025",))
    p = client.get(f"/api/studies/{sid}/profile").json()
    cav = next(c for c in p["caveats"] if c["key"] == "parties_missing")
    assert "2025" in cav["text"] and "road users" in cav["text"] and cav["limitation"]
    notes = {t["id"]: t.get("note") for t in p["tables"]}
    for tid in ("T2", "T10", "T16", "T17", "T19", "T20"):
        assert notes[tid] and "2025" in notes[tid], tid
    assert not notes["T4"] and not notes["T9"]                   # not built from Parties
    wb = load_workbook(io.BytesIO(client.get(f"/api/studies/{sid}/export.xlsx").content))
    sh = next(wb[n] for n in wb.sheetnames if n.startswith("T19"))
    assert any(r[0].value == "Note" and "2025" in str(r[1].value) for r in sh.iter_rows())
    text = " ".join(pg.extract_text() for pg in PdfReader(io.BytesIO(client.get(f"/api/studies/{sid}/export.pdf").content)).pages)
    assert "No CCRS party details for 2025" in text


def test_missing_injury_year_says_ksi_is_undercounted(client):
    sid = _study(client, drop=("InjuredWitnessPassengers_2024",))
    p = client.get(f"/api/studies/{sid}/profile").json()
    cav = next(c for c in p["caveats"] if c["key"] == "iwp_missing")
    assert "2024" in cav["text"] and "KSI" in cav["text"]
    assert "2024" in next(t for t in p["tables"] if t["id"] == "T3")["note"]


def test_nothing_missing_nothing_said(client):
    sid = _study(client)
    p = client.get(f"/api/studies/{sid}/profile").json()
    assert not {c["key"] for c in p["caveats"]} & {"parties_missing", "iwp_missing"}
    assert not any(t.get("note") for t in p["tables"])


def test_a_pull_missing_a_year_is_refreshed_daily_not_monthly():
    study = {"to_year": datetime.now(timezone.utc).year - 1}
    day_old = (datetime.now(timezone.utc) - timedelta(days=1, hours=1)).isoformat()
    assert crashes.stale({"pulled_at": day_old, "cleaning": {"parties_missing_years": [2025]}}, study)
    assert not crashes.stale({"pulled_at": day_old, "cleaning": {"parties_missing_years": []}}, study)
