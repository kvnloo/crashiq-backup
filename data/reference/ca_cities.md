# California incorporated cities (`ca_cities.csv`)

Used by the no-GPS city filter (#142, #147). A report filed under a name in this list is a real city; when the corridor
runs through unincorporated land, a report filed under any other name (an unincorporated place CHP files under its own
name: Kensington, Broadmoor, Bear Valley Springs, …) is treated like `Unincorporated` and kept.

- **Source:** CCRS City Names marked `City Is Incorporated = True` in 2021–2024 (Tester's CCRS mirror, copied
  2026-10-19), kept only when OpenStreetMap also has a city boundary (admin level 8; San Francisco: level 6) under
  that name (Tester's California extract, 2026-10-18). Name matching as in the app (`crashes.city_key`, prefixes).
- **480 rows:** 479 from both sources. Compton was added by hand: a real city, missing only from that OSM extract.
- **Left out:** CCRS marks these incorporated, but OSM has no city: Kensington (114 reports), Broadmoor (33),
  Bear Valley Springs (10), China Lake, plus park and college districts. CA has 482 incorporated cities. A real city
  missing here is never dropped by mistake: its reports are kept when the corridor is partly unincorporated.
