from crashiq.names import StreetKey, route_numbers, same_core, same_street, similarity, street_key, street_keys


def test_suffix_variants_collapse():
    assert street_key("ALEMANY BL") == street_key("Alemany Boulevard") == StreetKey("ALEMANY", "BLVD")
    assert street_key("MARINE AVE.") == street_key("MARINE AVENUE") == StreetKey("MARINE", "AVE")


def test_ordinals():
    assert street_key("07TH ST") == StreetKey("7TH", "ST")
    assert street_key("SEVENTH STREET") == StreetKey("7TH", "ST")


def test_noise_removed():
    assert street_key("147TH STREET (3100 BLOCK)") == StreetKey("147TH", "ST")
    assert street_key("W 147TH ST. E/B (3000 BLOCK)") == StreetKey("WEST 147TH", "ST")
    assert street_key("3144 W. 147TH ST ") == StreetKey("WEST 147TH", "ST")
    assert street_key("135TH STREET WESTBOUND") == StreetKey("135TH", "ST")


def test_routes():
    assert street_key("I-280 S/B") == StreetKey("I 280", None)
    assert street_key("US-101 N/B ") == StreetKey("US 101", None)
    assert street_key("SR-1 N/B TO US-101 N/B") == StreetKey("SR 1", None)


def test_same_street_ignores_missing_suffix_and_spaces():
    assert same_street(street_key("MASONIC"), street_key("MASONIC AVE"))
    assert same_street(street_key("BAY SHORE BLVD"), street_key("BAYSHORE BLVD"))
    assert not same_street(street_key("MISSION ST"), street_key("MISSION BAY BLVD"))


def test_similarity_catches_typos():
    assert similarity(street_key("MASSONIC AVE"), street_key("MASONIC AVE")) > 0.9
    assert similarity(street_key("GEARY BLVD"), street_key("GEARY ST")) < similarity(street_key("GEARY BLVD"), street_key("GEARY BLVD"))


def test_directional_kept_but_relaxable():
    from crashiq.names import same_core
    assert street_key("SOUTH VAN NESS AV") == StreetKey("SOUTH VAN NESS", "AVE")
    assert not same_street(street_key("SOUTH VAN NESS AV"), street_key("VAN NESS AVE"))
    assert same_core(street_key("W 147TH ST"), street_key("147TH ST"))


def test_empty():
    assert street_key(None) is None and street_key("  ") is None


def test_a_freeway_is_not_relaxed_to_a_street_of_the_same_name():
    # PM review of #72: HARBOR FWY (I-110) and HARBOR BLVD are different roads
    assert not same_core(street_key("HARBOR FWY"), street_key("HARBOR BLVD"))
    assert same_core(street_key("HARBOR FRWY"), street_key("Harbor Freeway"))
    assert same_core(street_key("HARBOR"), street_key("HARBOR FWY"))       # no suffix written: still relaxed


def test_avenue_of_keeps_of_and_matches_chp_spellings():
    # #154, Buellton: OSM 'Avenue of Flags'; CHP writes AVENUE OF FLAGS, AVE OF FLAGS, now and then AVENUE FLAGS
    k = street_key("Avenue of Flags")
    assert k.core == "AVENUE OF FLAGS"
    for chp in ("AVENUE OF FLAGS", "AVE OF FLAGS", "AV OF FLAGS", "AVENUE FLAGS"):
        assert same_core(street_key(chp), k), chp
    assert street_key("AV OF THE STARS").core == street_key("Avenue of the Stars").core == "AVENUE OF STARS"
    assert street_key("AVENUE OF THE FLAGS") == street_key("AVENUE OF FLAGS")          # CHP adds THE now and then
    assert street_key("100 FT NORTH OF THE BRIDGE").core == "FT NORTH BRIDGE"     # OF elsewhere is still noise


def test_leading_abbreviation_only_when_a_name_follows():
    # #212: AVE M = Avenue M, ST TROPEZ = Saint Tropez; but these keep their meaning
    assert street_key("W ST") == street_key("West Street")                         # ST last: Street
    assert street_key("N AVE") == street_key("North Avenue")
    assert street_key("W AVE J") == street_key("West Avenue J")
    assert street_key("100 FT NORTH OF THE BRIDGE").core == "FT NORTH BRIDGE"     # feet, not Fort
    assert street_key("ST HWY 1").core == "ST HWY 1"                                # not Saint Highway
    assert street_key("ST JOHNS AVE") == street_key("Saint Johns Avenue")


def test_pull_searches_chp_abbreviations_of_a_leading_word():
    from crashiq.crashes import _like_words, _search_words
    assert _like_words("AVENUE J") == ["AVENUE J", "AVE J", "AV J"]                 # CHP writes AVE J (#212)
    assert _like_words("SAINT TROPEZ") == ["SAINT TROPEZ", "ST TROPEZ"]
    assert _like_words("CRENSHAW") == ["CRENSHAW"]
    assert all(not route for _, route in _search_words("AVENUE J"))                 # not route spellings
    assert all(route for _, route in _search_words("SR 1"))


def test_chps_type_and_word_abbreviations_are_general_rules():
    # alias batch A (user 2026-10-22): these work in every city, not only where an alias row lists them
    pairs = [("MARTIN LUTHER KING JR WY", "Martin Luther King Junior Way"), ("ARROW RT", "Arrow Route"),
             ("ARROW RTE", "Arrow Route"), ("E CAPITOL EXPWY", "East Capitol Expressway"),
             ("W CAPITOL EX", "West Capitol Expressway"), ("ONTARIO MILLS PW", "Ontario Mills Parkway"),
             ("EAGLE GLEN PY", "Eagle Glen Parkway"), ("MOULTON PKY", "Moulton Parkway"),
             ("SILVERADO TRL", "Silverado Trail"), ("TWO BUNCH PALMS TR", "Two Bunch Palms Trail"),
             ("LAUREL CYN BL", "Laurel Canyon Boulevard"), ("OLD REDWOOD HW", "Old Redwood Highway"),
             ("PACIFIC COAST HWY - SR1", "Pacific Coast Highway"), ("BEACH BL - SR39", "Beach Boulevard"),
             ("TWIN PEAKS (N)", "Twin Peaks"), ("BALDWIN HTS DR", "Baldwin Heights Drive"),
             ("SAN BRUNO MTN RD", "San Bruno Mountain Road")]
    for raw, osm in pairs:
        assert street_key(raw) == street_key(osm), raw


def test_the_general_rules_dont_touch_what_they_shouldnt():
    assert street_key("RT 46") == StreetKey("SR 46", None)              # a route number, not "Route"
    assert street_key("ROUTE 66") == StreetKey("SR 66", None)
    assert street_key("STATE ROUTE 1") == StreetKey("SR 1", None)
    assert street_key("EXPO PARK DR").core == "EXPO PARK"               # EX only as a whole word, and last
    assert street_key("TRUMAN ST").core == "TRUMAN"
    assert street_key("ST JOHNS AVE").core == "SAINT JOHNS"            # #212 unchanged
    assert route_numbers("PACIFIC COAST HWY - SR1") == {"1"}            # the route still matches by number
    assert street_key("JR HIGH SCHOOL DR").core == "JUNIOR HIGH SCHOOL"


# D3 wording (#305): forms that hide a mapped street. Synthetic names, one case per form.
def test_a_route_tag_with_a_type_word_after_it():
    assert street_key("BEACH BL - SR39 BLVD") == street_key("Beach Boulevard")
    assert route_numbers("BEACH BL - SR39 BLVD") == {"39"}


def test_pk_is_parkway():
    assert street_key("HARBOR BAY PK") == street_key("Harbor Bay Parkway")
    assert street_key("SAN MIGUEL CYN RD") == street_key("San Miguel Canyon Road")


def test_state_routes_written_out():
    assert street_key("STATE HIGHWAY 96") == street_key("SR 96") == StreetKey("SR 96", None)
    assert street_key("STATE ROUTE 127") == StreetKey("SR 127", None)
    assert street_key("SH-60") == street_key("SH 60") == StreetKey("SR 60", None)
    assert route_numbers("SH-60") == {"60"}


def test_position_words_before_the_name():
    for raw in ("W CURB LINE OF LEMON ST", "WEST CURBLINE OF LEMON ST", "N SIDE OF LEMON ST", "NORTH OF LEMON ST",
                "100 FT NORTH OF LEMON ST", "E EDGE OF LEMON ST"):
        assert street_key(raw) == street_key("Lemon Street"), raw
    assert street_key("AVENUE OF THE STARS") == street_key("Avenue of the Stars")      # OF in a name: unchanged


def test_a_house_number_glued_to_the_street():
    assert street_key("2038 SAN MIGUEL CYN ROAD") == street_key("San Miguel Canyon Road")


def test_two_streets_in_one_field_are_each_tried():
    ks = street_keys("SOUTH WESTBORO AVE AND NORWICH AVE")
    assert street_key("South Westboro Avenue") in ks and street_key("Norwich Avenue") in ks
    assert street_keys("WESTBORO AVE & NORWICH AVE")[1:] == [street_key("Westboro Avenue"), street_key("Norwich Avenue")]
    assert street_keys("LEWIS AND CLARK DR")[0] == street_key("Lewis and Clark Drive")   # the whole name comes first
    assert street_keys("MAIN ST") == [street_key("Main Street")]
    assert street_keys(None) == []


def test_non_street_text_is_never_a_street():
    for raw in ("2 SOUTH GARFIELD PARKING LOT", "CITY POLE 120217634", "- ALY", "ALY", "PARKING STRUCTURE"):
        assert street_key(raw) is None, raw
        assert street_keys(raw) == [], raw
    assert street_key("POLE LINE RD") == StreetKey("POLE LINE", "RD")                 # a real street (Davis)
