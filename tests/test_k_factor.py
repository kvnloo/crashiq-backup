"""Volumes entered as peak-hour counts, converted to AADT with K (user, 2026-10-18: 10% is typical)."""
import io

from pypdf import PdfReader

from test_decisions_34 import _study


def _rates(client, sid):
    p = client.get(f"/api/studies/{sid}/profile").json()
    t2 = next(t for t in p["tables"] if t["id"] == "T2")
    return p, {r["key"]: r["values"]["rate"] for r in t2["rows"] if r["values"]["kind"] == "intersection"}


def test_peak_hour_with_k_matches_the_same_daily_volumes(client):
    a = _study(client)
    ints = client.get(f"/api/studies/{a}/network").json()["intersections"]
    for i in ints:
        client.patch(f"/api/studies/{a}/intersections/{i['id']}", json={"major_aadt": 32000, "minor_aadt": 12000})
    _, daily = _rates(client, a)

    b = _study(client)
    s = client.patch(f"/api/studies/{b}", json={"volume_basis": "peak_hour"}).json()
    assert (s["volume_basis"], s["k_factor"]) == ("peak_hour", 0.10)          # 10% default
    for i in client.get(f"/api/studies/{b}/network").json()["intersections"]:
        client.patch(f"/api/studies/{b}/intersections/{i['id']}", json={"major_aadt": 3200, "minor_aadt": 1200})
    p, peak = _rates(client, b)
    assert list(peak.values()) == list(daily.values()) and all(v is not None for v in peak.values())
    assert any(c["key"] == "aadt_from_peak_hour" and "K = 10%" in c["text"] for c in p["caveats"])
    text = " ".join(" ".join(pg.extract_text().split())
                    for pg in PdfReader(io.BytesIO(client.get(f"/api/studies/{b}/export.pdf").content)).pages)
    assert "estimated from peak-hour counts with K = 10%" in text


def test_k_factor_changes_the_estimate_and_is_bounded(client):
    sid = _study(client)
    client.patch(f"/api/studies/{sid}", json={"volume_basis": "peak_hour", "k_factor": 0.08})
    ints = client.get(f"/api/studies/{sid}/network").json()["intersections"]
    for i in ints:
        client.patch(f"/api/studies/{sid}/intersections/{i['id']}", json={"major_aadt": 3200, "minor_aadt": 1200})
    _, r8 = _rates(client, sid)
    client.patch(f"/api/studies/{sid}", json={"k_factor": 0.10})
    _, r10 = _rates(client, sid)
    first = ints[0]["id"]
    assert r8[first] < r10[first]                    # lower K → larger AADT → lower rate
    assert client.patch(f"/api/studies/{sid}", json={"k_factor": 0.5}).status_code == 422
    assert client.patch(f"/api/studies/{sid}", json={"volume_basis": "weekly"}).status_code == 422
