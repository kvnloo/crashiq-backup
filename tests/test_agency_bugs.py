"""Fixes for CCRS recording habits found by the Tester's statewide agency profile (#73). Each test started as a
strict xfail in tests/tester/test_ccrs_agency_bugs.py (feat/73-statewide-test)."""

from __future__ import annotations

import json

from crashiq import crashes
from crashiq.names import same_core, street_key
from crashiq.sources.ckan import Ckan
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)]
STUDY = {"from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100}
CROSS = ("Marine Avenue", "West 144th Street", "Rosecrans Avenue")
NET_X = {"line": LINE, "corridor_name": "Crenshaw Boulevard",
         "intersections": [{"name": n, "is_study": True} for n in CROSS]}


def _fixture(no_gps: bool = False) -> dict:
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    if no_gps:
        for rid, t in d["tables"].items():
            if rid.startswith("cra-"):
                for r in t["rows"]:
                    r["Latitude"], r["Longitude"] = "", ""
    return d


def _rename(d: dict, to: str) -> None:
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                for col in ("PrimaryRoad", "SecondaryRoad"):
                    if str(r.get(col) or "").upper().startswith("CRENSHAW"):
                        r[col] = to


# -- #80 hyphen in the corridor name ---------------------------------------------------------------------------
def test_hyphenated_corridor_name_finds_no_gps_reports():
    # Union City: OSM 'Alvarado-Niles Road', Union City PD (0% GPS) writes 'ALVARADO NILES RD'
    d = _fixture(no_gps=True)
    _rename(d, "ALVARADO NILES RD")
    out = crashes.pull(STUDY, {**NET_X, "corridor_name": "Alvarado-Niles Road"}, Ckan(FakeCkan(d)))
    assert {"9200001", "9200002", "9200003"} <= {c["crash_id"] for c in out["crashes"]}


def test_hyphen_written_in_the_report_matches_too():
    d = _fixture(no_gps=True)
    _rename(d, "ALVARADO-NILES RD")
    out = crashes.pull(STUDY, {**NET_X, "corridor_name": "Alvarado Niles Road"}, Ckan(FakeCkan(d)))
    assert {"9200001", "9200002", "9200003"} <= {c["crash_id"] for c in out["crashes"]}


def test_hyphen_is_a_space_in_street_keys_but_routes_keep_their_number():
    assert street_key("Alvarado-Niles Road") == street_key("ALVARADO NILES RD")
    assert same_core(street_key("ALVARADO-NILES"), street_key("Alvarado Niles Road"))
    assert street_key("I-880").core == "I 880" and street_key("SR-1").core == "SR 1"
