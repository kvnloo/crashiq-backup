"""Which state-highway rate a crash counts in (#304; user decisions 2026-10-31/11-01, docs/03 #297). Synthetic only."""

import pytest

from crashiq import rate_class

CONV = {"corridor_names": ["Pacific Coast Highway", "CA 1"], "is_freeway": False}
FWY = {"corridor_names": ["San Diego Freeway", "I 405"], "is_freeway": True}


def c(p, s, ft=None):
    return {"crash_id": "x", "primary_road": p, "secondary_road": s, "offset_ft": ft}


@pytest.mark.parametrize("net, crash, want", [
    # on the highway's own roadway
    (CONV, c("PACIFIC COAST HWY", "MAIN ST", 120), ("mainline", "on the highway")),
    (CONV, c("SR-1", "MAIN ST"), ("mainline", "on the highway")),
    (FWY, c("I-405", "VERMONT AVE", 500), ("mainline", "on the highway")),
    # a route-to-route connector with a local cross street stays mainline (2026-10-25)
    (FWY, c("I-405 NB TO I-110", "VERMONT AVE", 300), ("mainline", "on the highway")),
    # ramps: a ramp word, "<route> <dir> TO <local street>", a connector whose cross street is one of the routes
    (FWY, c("I-405 NB OFF RAMP", "VERMONT AVE"), ("ramp", "names a ramp")),
    (FWY, c("I-405 S/B TO VERMONT AVE", "VERMONT AVE"), ("ramp", "<route> <dir> TO <street>: the off-ramp")),
    (FWY, c("I-405 NB TO I-110", "I-110"), ("ramp", "freeway connector")),
    (FWY, c("REDONDO BEACH BLVD. TO I-405 NB", "REDONDO BEACH BLVD."), ("ramp", "<street> TO <route> <dir>: the on-ramp")),
    # conventional highway: a cross-street primary at the intersection counts (answer 3; blank = 0; within radius)
    (CONV, c("MAIN ST", "PACIFIC COAST HWY"), ("mainline", "at an intersection")),
    (CONV, c("MAIN ST", "PACIFIC COAST HWY", 0), ("mainline", "at an intersection")),
    (CONV, c("MAIN ST", "PACIFIC COAST HWY", 250), ("mainline", "at an intersection")),
    (CONV, c("MAIN ST", "PACIFIC COAST HWY", 251), ("cross_street", "cross street, beyond 250 ft")),
    (CONV, c("PCH FRONTAGE RD", "MAIN ST", 100), ("cross_street", "cross street or frontage road")),
    # #314 review: the route by number though the field adds the freeway's name; another route's main lanes are out
    (FWY, c("NORTHBOUND I-405 SAN DIEGO FREEWAY", "HAWTHORNE BLVD"), ("mainline", "on the highway")),
    (FWY, c("I-110 S/B TO I-405 N/B", "190TH ST"), ("cross_street", "on another route's main lanes (I-110)")),
    # freeway: any cross-street primary is out, whatever the distance
    (FWY, c("VERMONT AVE", "I-405", 0), ("cross_street", "cross street on a freeway")),
])
def test_rate_class(net, crash, want):
    assert rate_class.classify(crash, net, radius_ft=250) == want


def test_the_intersection_test_is_one_function_with_the_study_radius():
    assert rate_class.at_intersection(c("MAIN ST", "PCH", None), 250)
    assert rate_class.at_intersection(c("MAIN ST", "PCH", 300), 400)
    assert not rate_class.at_intersection(c("MAIN ST", "PCH", 300), 250)


SEGS = [{"id": "S1", "from_station_ft": 0, "to_station_ft": 1000},
        {"id": "S2", "from_station_ft": 1000, "to_station_ft": 2500}]
X = {"id": "I2", "station_ft": 1000}
LAST = {"id": "I3", "station_ft": 2500}


def test_an_intersection_crash_goes_to_the_segment_on_its_gps_side():
    assert rate_class.segment_for(X, SEGS, 900) == "S1"
    assert rate_class.segment_for(X, SEGS, 1100) == "S2"


def test_no_gps_or_within_25_ft_of_the_station_goes_to_the_segment_after():
    assert rate_class.segment_for(X, SEGS, None) == "S2"
    assert rate_class.segment_for(X, SEGS, 980) == "S2"           # 20 ft before: GPS noise, at the station
    assert rate_class.segment_for(X, SEGS, 974) == "S1"


def test_the_last_intersection_gives_its_crashes_to_the_segment_before():
    assert rate_class.segment_for(LAST, SEGS, None) == "S2"
    assert rate_class.segment_for(LAST, SEGS, 2600) == "S2"
