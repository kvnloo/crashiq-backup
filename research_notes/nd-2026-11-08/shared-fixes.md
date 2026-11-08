# Shared fixes from North Dakota (2026-11-08)

1. `backend/scripts/build_state_county_boxes.py`: `STATE_FIPS` lacks `"ND": "38"` (and `"AK": "02"`). I built `data/reference/county_boxes_nd.json` with the same logic in a scratch script (Census cb_2024 county file, box + 5 km). Fix: add the codes. Test: `main(zip, ["ND"])` writes 53 counties.

Nothing else: the reader writes no street names, so the locator and `names.py` aren't touched.
