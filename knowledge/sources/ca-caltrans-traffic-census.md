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
  Truck points are far apart, so one point's ahead leg can cover miles (2024: LA-405 12.97 to 17.589; SM-82 3.435
  to 10.554), and some points carry only a back leg (LA-405 17.589). Truck-involved rates (T24, #287) use the 3+ axle
  count (TRK_3 + TRK_4 + TRK_5) of the truck point behind. Hand check, Engineering, 2026-10-29: LA-405 PM 13.5
  4,919 (2021) and 5,185 (2024) 3+ axle trucks of 270,000 / 285,000 AADT (1.8%); SM-82 PM 9.0 (El Camino Real) 200
  to 232 of 29,500 to 34,000 (0.7%); LA-5 PM 20.0 about 10,100 of 206,000 (4.9%).
- **Ramps:** per-district ramp ADT workbooks on the same page (2017–2024 as .xlsx, 2016 as PDF). Each edition holds
  ten years of counts per ramp (YR_2015 … YR_2024 in the 2024 edition), one row per ramp: route, county, postmile,
  and a free-text description ("SB OFF TO VERMONT AVE", "099/NB ON FR BELLEVUE RD", "NBOFF TRAVER/MERRITT DR",
  "NORWOOD TO WB-80"). Ramps are counted on rotation, so most years are blank. Rows starting "SEG" are pieces of a
  ramp; "CONN" rows are freeway connectors. The preface sheet is an image, and nothing on the page explains the
  values 1001 and 999, which appear in every district: runs of 1001 ending in 999 on closed ramps (LA-405 "SB OFF
  TRUCK SCALES (CLOSED)": 1001, 999) and a lone 999 between real counts (LA-405 "NB ON FROM WB RTE 105": 9,793 in
  2020, 999 in 2021, 33,373 in 2022). CrashIQ treats both as missing (pain point 38). Engineering's copy, 2026-10-30:
  48 files (2021–2024, 12 districts, 16.5 MB): 14,356 distinct ramp rows, 13,297 with at least one real count;
  5,650 placeholder values left out.
  - **Use in CrashIQ (#287 ramps, user decision 2026-10-30, #300):** a ramp crash's ramp is identified when exactly
    one ramp within 0.3 mi fits the report's direction, on/off and cross street (`backend/crashiq/ramps.py`); the
    engineer picks when 2 or more fit. A year's ramp ADT is the latest count at or before it, never a later one,
    and a count more than 5 years before the year is too old to use (user decision 2026-11-01): no rate, and the row
    says "count too old".
  - **Measured (Engineering, 2026-10-30)** on the Tester's 4,424 statewide ramp crashes with a derived postmile
    (#292, `aadt_match.csv`): identified 2,094 (47%); 2 or more fit 186; no ramp rate 2,144. The no-rate reasons:
    no ramp fits 1,137 (mostly CHP's compass direction against Caltrans' route direction, or a cross street missing
    from the description); no ramp within 0.3 mi 286; no direction in the report 240; no cross street 204; on or
    off not stated 156; two or more of these missing 121. On the identified crashes the count used is 0 years old
    for 382, 1–4 years for 947, 5–9 for 546, 10–14 for 121, and 98 have no count at or before the crash year.
- **Where:** https://dot.ca.gov/programs/traffic-operations/census (public; Caltrans), fetched with the honest
  `CrashIQ/0.1` user agent (dot.ca.gov serves it, checked 2026-10-26). The files by year are listed in
  `backend/crashiq/config/aadt.json`. The ArcGIS layers `CHhighway/Traffic_AADT` and `CHhighway/Truck_Volumes_AADT`
  hold one year's points with coordinates but no year field, so CrashIQ uses the annual workbooks.
- **Formats:** the column names change between years (`ROUTE`/`RTE`, `COUNTY`/`CNTY`, `LOCATION DESCRIPTION`/
  `DESCRIPTION`, `POSTMILE`/`PM`); blanks come as empty, a space or nothing; postmiles as text (".129") or numbers;
  routes zero-padded ("001"). The first sheet is a preface.
- **Count years 2016–2020 (#345, user OK 2026-11-01):** the volume and truck workbooks of those years, downloaded by
  the PM session into `data/cache/caltrans_downloads_2026-11-01/` with `SHA256SUMS`; `aadt.py` reads a workbook from
  there first (by the URL's file name, checksum matched), so it is never downloaded twice. Their layouts differ:
  2016's volume sheet has no header row (2017's columns); 2018 writes 0 where other years leave a count blank (read
  as no count); 2016–2018 truck sheets have a three-row header and a combined postmile ("R0.129", "R.78") with no
  suffix columns; 2019–2020 truck sheets spell POSTMILE_PFX / POSTMILE_SFX / TRUCK_AADT_TOTAL. Parsed (Engineering,
  2026-11-01): count points 2016 7,056 / 2017 7,093 / 2018 7,154 / 2019 7,120 / 2020 7,114 (about 6,400 a year
  with an ahead AADT); truck points 3,429–3,482. LA-405 at PM 13.5: 285,000–286,000 AADT 2016–2019, 256,000 in 2020.
  Ramp counts for those years come from the 2021+ ramp editions (ten years each).
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
