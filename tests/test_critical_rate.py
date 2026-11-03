"""#34 item 7: critical rate against similar sites on the corridor (HSM Ch. 4 critical rate method)."""
import io
import math

import pytest
from pypdf import PdfReader

from crashiq import profile

from test_decisions_34 import _study


def test_critical_rate_matches_a_hand_calculation():
    sites = [("a", 10, 5.0), ("b", 4, 4.0), ("c", 20, 6.0), ("d", 2, 3.0)]
    ra, rc = profile.critical_rates(sites)
    assert ra == pytest.approx(36 / 18)                                  # Σ crashes / Σ exposure = 2.0
    assert rc["c"] == pytest.approx(2.0 + 1.645 * math.sqrt(2.0 / 6.0) + 1 / 12)
    assert rc["d"] > rc["c"]                                             # less exposure → wider band


def test_no_reference_average_from_fewer_than_three_sites():
    assert profile.critical_rates([("a", 3, 2.0), ("b", 5, 1.0)]) == (None, {})
    assert profile.critical_rates([("a", 3, 2.0), ("b", 5, None), ("c", 1, None)]) == (None, {})


def test_exposure_units():
    assert profile.exposure("intersection", 5, 40000) == pytest.approx(40000 * 365 * 5 / 1e6)     # MEV
    assert profile.exposure("segment", 5, 30000, 0.2) == pytest.approx(30000 * 365 * 5 * 0.2 / 1e8)  # 100M VMT


def _t2(client, sid):
    p = client.get(f"/api/studies/{sid}/profile").json()
    return p, {r["key"]: r["values"] for r in next(t for t in p["tables"] if t["id"] == "T2")["rows"]}


def test_crenshaw_intersections_against_their_own_average(client):
    sid = _study(client)
    ints = client.get(f"/api/studies/{sid}/network").json()["intersections"]
    for i in ints[:2]:
        client.patch(f"/api/studies/{sid}/intersections/{i['id']}", json={"major_aadt": 32000, "minor_aadt": 12000})
    p, rows = _t2(client, sid)
    assert rows[ints[0]["id"]]["critical_rate"] is None
    assert any(c["key"] == "critical_intersection" and "(2 entered)" in c["text"] for c in p["caveats"])
    for i in ints[2:]:
        client.patch(f"/api/studies/{sid}/intersections/{i['id']}", json={"major_aadt": 32000, "minor_aadt": 12000})
    p, rows = _t2(client, sid)
    vals = [rows[i["id"]] for i in ints]
    n = sum(v["crashes"] for v in vals)
    e = sum(profile.exposure("intersection", 5, profile.entering_volume(32000, 12000, i["legs"])) for i in ints)
    assert vals[0]["reference_rate"] == pytest.approx(round(n / e, 2))
    for v in vals:
        assert v["over_critical"] == ("Yes" if v["rate"] > v["critical_rate"] else "No") or abs(v["rate"] - v["critical_rate"]) < 0.01
    cav = next(c for c in p["caveats"] if c["key"] == "critical_rate")
    assert "not statewide averages" in cav["text"] and cav["count"] == sum(v["over_critical"] == "Yes" for v in vals)
    seg = next(v for k, v in rows.items() if k.startswith("seg"))
    assert seg["critical_rate"] is None                                    # segments: no AADT entered


def test_pdf_shows_critical_rates_and_says_what_they_compare(client):
    sid = _study(client)
    for i in client.get(f"/api/studies/{sid}/network").json()["intersections"]:
        client.patch(f"/api/studies/{sid}/intersections/{i['id']}", json={"major_aadt": 32000, "minor_aadt": 12000})
    text = " ".join(" ".join(pg.extract_text().split())
                    for pg in PdfReader(io.BytesIO(client.get(f"/api/studies/{sid}/export.pdf").content)).pages)
    assert "Critical (95%) Over?" in text                                 # the T2 columns
    assert "compared with its critical rate (HSM Ch. 4, 95% confidence)" in text
    assert "does not compare rates with statewide averages" in text


# ODOT Analysis Procedures Manual v2, Ch. 4 (12/2025), Example 4-3 "HSM Critical Rate for Intersections with Internal
# Reference Population", pp. 4-27 to 4-32: the six unsignalized intersections on Main St. (Type 1 population), 5 years
# (2005-2009). Daily entering volume, total crashes and Fatal + Injury-A crashes from the p. 4-30 table (F+A from the
# severity table, p. 4-29); the book's critical rates from the tables on pp. 4-31 and 4-32.
ODOT_4_3 = [  # (intersection, daily entering volume, all crashes, F+A crashes, book Rc all, book Rc F+A)
    ("Water St.", 7600, 6, 2, 0.39, 0.17),
    ("1st St.", 6700, 0, 0, 0.41, 0.18),
    ("2nd St.", 10900, 1, 0, 0.35, 0.14),
    ("4th St.", 21500, 2, 0, 0.29, 0.11),
    ("6th St.", 22300, 14, 5, 0.29, 0.11),
    ("8th St.", 19800, 5, 0, 0.30, 0.11),
]


@pytest.mark.parametrize("col, book_ra, book_over", [
    (2, 0.17, {"Water St.", "6th St."}),       # all crashes: Ra p. 4-30, Over p. 4-31
    (3, 0.04, {"6th St."}),                     # Fatal + Injury-A: Ra p. 4-30, Over pp. 4-31 to 4-32
])
def test_odot_apm_example_4_3(col, book_ra, book_over):
    mev = {r[0]: profile.exposure("intersection", 5, r[1]) for r in ODOT_4_3}   # MEV = volume × 365 × 5 / 10^6
    ra, rc = profile.critical_rates([(r[0], r[col], mev[r[0]]) for r in ODOT_4_3])
    assert round(ra, 2) == book_ra
    assert {k: round(v, 2) for k, v in rc.items()} == {r[0]: r[col + 2] for r in ODOT_4_3}
    assert {r[0] for r in ODOT_4_3 if r[col] / mev[r[0]] > rc[r[0]]} == book_over   # step 5: flagged for review
