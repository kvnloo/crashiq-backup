# Shared fixes Mississippi would like (not made; Hermes merges centrally)

1. **`names.py` doesn't read `MS 25` as a state route.** `street_key("MS 25")` is `MS 25`, and `ROUTE_ANY` finds no
   route number in it, so a crash on "MS 25" wouldn't match a corridor whose OSM ref is "MS 25" by route number.
   Workaround in the reader: bare state-highway numbers are written `MS 25`, which matches a corridor tagged
   `MS 25` by name (same core), though not by route number. The first end-to-end run wrote `SR 25` and lost 148
   Lakeland Drive crashes to "not on the corridor street". Fix: add the two-letter state prefix
   of the active pack to `ROUTE` / `ROUTE_ANY` / `ROUTE_SPELLINGS["SR"]`.
   Test: `assert street_key("MS 25").core == "SR 25"` and `route_numbers("MS-25") == {"25"}`.
2. **Two streets in one field** (`Pear Orchard Dr. / North Town Dr.`, `Ridgewood Rd/Old Canton Rd`): the locator
   reads it as one name. Not worked around (GPS covers every MS crash).
