# Shared fixes Arkansas needs (not made on this branch)

## 1. Street names written without spaces (ARDOT)
ARDOT's road id carries the street as `NRODNEYPARHAMRD`, and ~19% of its cross streets look the same
(`KAVANAUGHBLVD`, `SSHACKLEFORDRD`). `names.street_key` keys on words, so these never match the corridor's
"North Rodney Parham Road", and `assign._names` returns False: a GPS crash inside the radius would be excluded as
`not_on_corridor_street`. Workaround here: the reader sets both road fields to None (GPS-only placement, like a
CCRS crash with blank roads).

Fix: compare a squeezed form as a fallback, e.g. in `crashes._names_street`:
```python
squeeze = lambda s: re.sub(r"[^A-Z0-9]", "", s.upper())
# match when squeeze(raw) equals squeeze(name) for any corridor name or alias (with and without direction/type)
```
Test: `_names_street("NRODNEYPARHAMRD", keys_for("N Rodney Parham Rd"))` is True and
`_names_street("RESERVOIRRD", same)` is False. Then the reader can fill `primary_road` from the road id
(`AH_RoadID.split("x")[1]`, a number means a highway: "AR 10" / "US 70" / "I 630" by RoadSystem).

## 2. "AR" route prefix
`names._street_key_ours` maps `CA` to SR but not `AR` (nor any other state's prefix). Arkansas writes state
highways "AR 10" / "Hwy 10". Fix: accept the pack's state code as a state-route prefix. Test: `street_key("AR 10")
== street_key("SR 10")`.

## 3. `tests/test_packs.py::test_setup_lists_ready_states_first` fails with Arkansas
It asserts `s[0]` is California, but `packs.states()` sorts ready states alphabetically, so Arkansas (and
Alabama, Alaska, Arizona later) comes first. Either the test checks `{"code": "CA", ...} in ready`, or `states()`
pins California first (a product choice). This branch adds no shared edit, so this one test fails here.

## 4. Default window before a pack's first year
`study.default_window` doesn't clamp to `pack.first_year`; a study created without years fails validation when the
source starts after `last_final_year - 4`. Arkansas sets `final_lag_months=10` (true for ARDOT's yearly posting) so
the default is 2021-2025. Fix: `from_ = max(to - DEFAULT_YEARS + 1, pack.first_year)`.
