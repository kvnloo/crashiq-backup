from crashiq import pcf


def test_parse_ccrs_spellings():
    assert pcf.parse("VC 22350") == ("22350", "")
    assert pcf.parse("21658(A)") == ("21658", "A")
    assert pcf.parse("22107 CVC") == ("22107", "")
    assert pcf.parse("VC 21651(A1)") == ("21651", "A")
    assert pcf.parse("  ") == "blank"
    assert pcf.parse("UNSAFE BACKING") == "words"


def test_split_keys_take_their_2024_category():
    # user decision 2026-10-20 (docs/03): CHP's 2024 category for every year
    assert pcf.category("VC 21954") == "10"                  # 2021-23 00, 2024 10 Pedestrian Right of Way
    assert pcf.category("21955(A)") == "10"
    assert pcf.category("23103(A)") == "17"
    assert pcf.category("21809(A)") == "17"                  # 09 in 2021-23, 17 in 2024: 2024 wins
    assert pcf.category("21223(A)") == "14" and pcf.labels()["14"] == "Lights"
    assert pcf.category("22106(1)") == "unknown"             # 2024 gives 00
    assert pcf.category("21760(A)") == "split"               # no 2024 records: left as split
    split = [k for k, (st, _, _) in pcf.table().items() if st == "split"]
    assert split == [("21760", "A")]
