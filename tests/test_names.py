from crashiq.names import StreetKey, same_street, similarity, street_key


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
