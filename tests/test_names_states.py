"""Route spellings other states write (#19 state packs; the build sessions' shared-fixes.md, 2026-11-08)."""

import pytest

from crashiq.names import route_numbers, street_key


@pytest.mark.parametrize("raw, tiger", [
    ("CT 187", "State Rte 187"), ("AR 10", "State Hwy 10"), ("MS-25", "State Hwy 25"), ("KY1747", "KY 1747"),
    ("MNTH 13", "State Hwy 13"), ("ISTH 94", "I- 94"), ("USTH 169", "US Hwy 169"), ("PA 611", "SR 611"),
])
def test_another_state_s_route_prefix_is_a_state_route(raw, tiger):
    assert street_key(raw) == street_key(tiger)


def test_a_direction_before_the_route_doesn_t_hide_it():
    assert street_key("SB I-35E") == street_key("I-35E") and street_key("NB US 52") == street_key("US 52")


@pytest.mark.parametrize("raw", ["IN 200 BLOCK MAIN ST", "OR 99", "ME 9", "CO 81", "NE 45TH ST", "MI 5"])  # stay as written
def test_word_like_codes_are_not_routes(raw):
    k = street_key(raw)
    assert k is None or not k.core.startswith("SR ")


def test_route_numbers_read_state_prefixes_but_not_words():
    assert route_numbers("MS-25 AT MAIN") == {"25"} and route_numbers("IN 200 BLOCK") == set()


def test_california_spellings_are_unchanged():
    assert street_key("CA 1").core == "SR 1" and street_key("SR-1").core == "SR 1" and street_key("I-405 S/B").core == "I 405"
    assert street_key("PACIFIC COAST HWY").core == "PACIFIC COAST"


def test_nashville_pke_is_pike():
    assert street_key("NOLENSVILLE PKE") == street_key("Nolensville Pike")
