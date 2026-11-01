# Caltrans postmiles (SHN Postmiles Tenth)

- **What:** a point every 0.1 mile along every California state route (Interstate, US and State highways), each side
  of a divided road on its own (`AlignCode` Left / Right, `Direction` NB / SB / EB / WB), with the route, county,
  postmile prefix (R, M, ... for realignments), postmile, postmile suffix (independent alignments) and odometer.
  Postmiles restart at county lines. Public, from Caltrans' Transportation System Network (TSN).
- **Where:** https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/SHN_Postmiles_Tenth/FeatureServer/0
  (also listed on data.ca.gov). Pulled through `/query` with `outSR=4326`, 2,000 rows a page ordered by OBJECTID.
- **Vintage:** the layer reports no edit date, so the download date is the vintage. Tester's copy: 2026-10-24,
  311,198 points (`Crash-tester/data/cache/postmiles/`, with SOURCE.md); the app downloads the same way into
  `data/cache/postmiles/shn_postmiles_tenth_<date>.sqlite` and refreshes after a year.
- **Use in CrashIQ (#248, user decision 2026-10-23):** the postmile of a counted crash on a state route, interpolated
  between the two 0.1-mile points that bracket where CrashIQ placed it (within 100 m of the route; the side of the
  stated travel direction first). Marked derived: CHP's CCRS tables carry no postmile CrashIQ uses, and the postmile
  never changes placement. It lets Caltrans users match crashes against TASAS (`ca-caltrans-tasas.md`).
- **Mile markers to a point (#319, user decision 2026-11-01; behind a switch):** the reverse lookup. A postmile on a
  route in a county is interpolated between the tenth points of every line (alignment, prefix, suffix) that spans it;
  lines within 0.1 mi are one place (the two sides of a divided road), farther apart are two (a realignment, R vs no
  prefix) and the crash goes to review. Counties: the layer's 58 Caltrans abbreviations, matched to CCRS county codes
  1-58 (`postmile.COUNTY`). First look on 226 CCRS crashes with police GPS: median 375 ft, 53.5% within 0.1 mi.
