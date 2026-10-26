# Caltrans Traffic Census Program (state-highway AADT)

- **What:** annual average daily traffic (AADT) at count points along every California state route. Each row gives
  the route (and route suffix), county, postmile prefix, postmile and postmile suffix, a location description, and
  the AADT, peak-hour volume and peak-month ADT just behind the point (BACK) and just ahead of it (AHEAD). A count
  year runs October 1 to September 30. Most points are counted by portable counters in a rotating sample and
  adjusted to an annual estimate; many points repeat the previous year's value when they weren't recounted. Rows
  described "BREAK IN RTE" or "ROUTE BREAK AHEAD" mark gaps in a route, with no AADT across them. Caltrans explains
  the back and ahead legs in its diagram "Back and Ahead Leg Traffic Count" (PDF, on the census page):
  https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/back-and-ahead-leg-traffic-count-diagram-a11y.pdf
- **Truck AADT:** a separate annual workbook, a row per leg (B behind, A ahead) at fewer points, with total vehicle
  AADT, truck AADT and the 2-, 3-, 4- and 5+-axle counts and shares.
- **Ramps:** per-district ramp ADT workbooks (2016 to 2024) on the same page. Not loaded yet (#287 follow-up).
- **Where:** https://dot.ca.gov/programs/traffic-operations/census (public; Caltrans), fetched with the honest
  `CrashIQ/0.1` user agent (dot.ca.gov serves it, checked 2026-10-26). The files by year are listed in
  `backend/crashiq/config/aadt.json`. The ArcGIS layers `CHhighway/Traffic_AADT` and `CHhighway/Truck_Volumes_AADT`
  hold one year's points with coordinates but no year field, so CrashIQ uses the annual workbooks.
- **Formats:** the column names change between years (`ROUTE`/`RTE`, `COUNTY`/`CNTY`, `LOCATION DESCRIPTION`/
  `DESCRIPTION`, `POSTMILE`/`PM`); blanks come as empty, a space or nothing; postmiles as text (".129") or numbers;
  routes zero-padded ("001"). The first sheet is a preface.
- **Vintage:** the download date. Engineering's check copy, 2026-10-26: count years 2021 (7,116 points, 3,467 truck
  rows), 2022 (7,116 / 3,467), 2023 (7,134 / 3,461), 2024 (7,258 / 3,463). The app downloads into
  `data/cache/aadt/caltrans_aadt_<date>.sqlite` and refreshes after a year.
- **Between count points the volume changes.** On 2024's 6,527 segments between consecutive points, the AHEAD AADT of
  one point and the BACK AADT of the next are equal on 3,815, differ by under 5% on 686, by 5 to 20% on 1,033, and by
  20% or more on 943 (long rural stretches, e.g. MON-1 Big Sur 35.3 to 46.6: 1,700 then 3,500). 938 segments change
  postmile prefix between their ends, so their postmile length is approximate.
- **Use in CrashIQ (#287, user decision 2026-10-26):** a state-highway crash's AADT comes from its derived postmile
  (#248) and its count year: the AHEAD leg of the point behind it in the first half of the segment, the BACK leg of
  the point ahead in the second half. A year after the newest file uses the newest, labelled "latest available".
  Rates: crashes per million vehicle-miles = crashes / (AADT x length mi x 365 x years) x 10^6.
- **Hand checks (#287 point 4, Engineering, 2026-10-26, 2024 counts):**
  - BUT-99, the 51k → 86k jump is in Caltrans' counts: Chico's freeway section runs East 20th St (R31.498)
    47,500 back / 65,000 ahead, Jct Rte 32 East (R32.445) 65,000 / 86,000, East First Ave (R33.282) 86,000 / 60,000,
    Cohasset Hwy (R34.245) 60,000 / 49,500. The join reproduces the source; the jump is real traffic.
  - SR-9: 2,100 to 7,400 AADT outside Saratoga, Los Gatos and Felton (SCR-9 R20.858 Waterman Gap 2,100 / 2,500), so
    rates per million vehicle-miles are high on low volume; the AADT side matches the workbook. A sharp step at its
    south end: SCR-9 0.046 (Jct Rte 1) 25,500 ahead, then 0.63 (Santa Cruz north city limits) 5,700 back; with the
    nearer-leg rule a short segment there gets 25,500 or 5,700 depending on its half.
- **Use in rates (#287 PR 2):** each study segment is sampled every 0.05 mi; a calendar year is 0.75 x its count year +
  0.25 x the next (count years run October to September). A segment-year has exposure only when every sample has a
  count. Lengths come from the study geometry, never from postmiles, so a prefix change doesn't distort them.
