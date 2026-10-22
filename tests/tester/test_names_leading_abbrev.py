"""#212 (Tester, #211 audit): a street-type or title abbreviation at the start of a name must match the spelled-out
name, as suffix abbreviations already do. Strict xfail: passes (and must then be un-marked) once #212 is fixed."""
import pytest

from crashiq.names import same_core, street_key

PAIRS = [("AVE M", "Avenue M"), ("AV J", "Avenue J"), ("AVE Q-8", "Avenue Q-8"), ("ST TROPEZ CT", "Saint Tropez Court"),
         ("MT VERNON AVE", "Mount Vernon Avenue"), ("FT STOCKTON DR", "Fort Stockton Drive"),
         ("BL DE ORO", "Boulevard de Oro")]


@pytest.mark.parametrize("report,osm_name", PAIRS)
def test_leading_abbreviation_matches_spelled_out_name(report, osm_name):
    assert same_core(street_key(report), street_key(osm_name))


def test_already_working_cases_stay_working():
    assert same_core(street_key("AVE OF THE STARS"), street_key("Avenue of the Stars"))
    assert same_core(street_key("FOOTHILLS BL"), street_key("Foothills Boulevard"))
