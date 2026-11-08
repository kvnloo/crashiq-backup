"""Tester (on #420, head c2d0517): a crash reported at a signalized driveway that #420 makes a study intersection isn't
placed there. The pull no longer excludes it (its cross street now names a study intersection), but the street-name
locator works on the street network (overpass_query), which has no `service` ways, so the crash stays `unmatched`.
Frozen run: 75 crashes in 10 corridors (Dana Point "PCH / DOHENY PARK PLZ" 15+, Signal Hill "TOWN CENTER" 23, ...)."""

from crashiq import network, placement

from test_driveways import LINE, MAIN, drive


def test_a_crash_at_a_named_signalized_driveway_is_placed_at_it():
    found = network.detect(MAIN, LINE, driveways=drive("Corte Madera Town Center"))
    net = {"line": LINE, **found, "intersections": [{**i, "is_study": True} for i in found["intersections"]]}
    at = next(i for i in net["intersections"] if i["name"] == "Corte Madera Town Center")
    crash = {"crash_id": "1", "primary_road": "MAIN ST", "secondary_road": "CORTE MADERA TOWN CENTER", "offset_ft": 0,
             "offset_dir": None, "location_source": "unmatched", "lat": None, "lon": None, "severity": "C",
             "killed": 0, "year": 2024}
    control = {**crash, "crash_id": "2", "secondary_road": "1ST ST"}      # a street the locator does know
    result = {"crashes": [crash, control], "cleaning": {}}
    placement.place_unmatched(None, net, result, raw=MAIN)
    assert control["location_source"] == "exact"
    assert crash["location_source"] != "unmatched", crash          # c2d0517: still unmatched
    assert abs(crash["lat"] - at["lat"]) < 0.0005 and abs(crash["lon"] - at["lon"]) < 0.0005
