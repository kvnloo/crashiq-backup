# Colorado: crash data import (Hermes, 2026-11-08)

Bucket **A** (verified live 2026-11-08): open yearly statewide listings, record-level, GPS plus the reported street
pair, KABCO people counts. Status **active** (end-to-end check passed), with a download catch. Licence for paid use:
**unclear**.

## 1. Source: CDOT Statewide Crash Data Listing
- Page: https://www.codot.gov/safety/traffic-safety/data-analysis/crash-data — "Statewide Crash Data Listing (2007
  through 2026)", one Excel file per year plus two data dictionaries (2007-2020, 2021-2026), each an OnBase DocPop
  link on oitco.hylandcloud.com/CDOTRMPop, anonymous. Update log on the page: 2025 listing "considered complete"
  2026-07-23; 2026 preliminary, updated 2026-10-09; "All crash data from 2021 to 2026 is subject to updates".
- CDOT gets every crash in DOR's DRIVES system "excluding private property and counter reports", then cleans and
  normalizes it (page, "Process").
- Rows (2021-on layout, 110 columns): 2021 97,788 · 2022 95,380 · 2023 102,768 · 2024 100,680 · 2025 95,696.
- GPS (plausible, inside Colorado): 2021 75.8% · 2022 84.1% · 2023 92.5% · 2024 97.8% · 2025 99.75%.
- Street pair (Location 1 + Location 2, mile markers dropped): 2021 84% … 2024 82%, 2025 82%. The Link field gives the
  offset: "AT", "00201FN" (201 ft north), "0.25MW", "S/O"; on state highways Location 2 is often "MM 29.988" (18% of
  2024 rows), which the reader drops as a cross street.
- Severity: people at each level, Injury 00 (O) … Injury 04 (K) (dictionary 2021-2026); crash severity = the worst
  person's. 2024: K 642 · A 3,343 · B 10,815 · C 12,014 · O 73,866.
- Also: CUID (crash id), system code (City Street, County Road, State Highway, Interstate Highway, Frontage Road),
  route and milepoint, agency, city, county, crash type, harmful events, light, weather, road condition, and the first
  two traffic units' type, movement, direction, speed, driver action, human factor, age, sex, alcohol/marijuana, and
  non-motorist type. No person or vehicle tables.
- 2007-2020: another layout (84 columns, no CUID, upper-case values). Not read yet; `years_missing`.

## 2. Licence
CDOT's page, quoted 2026-11-08: "CDOT maintains a crash database for the purpose of improving traffic and highway
safety as required by 23 U.S.C. Section 148 and 23 U.S.C. Section 405. All crash data listings, reports and dashboards
are protected under 23 U.S.C. Section 407." No reuse grant, no ban: **unclear** for a paid product.
Contacts on the page: David Swenka, P.E., PTOE (david.swenka@state.co.us); Aaron Moss, Crash Data Analyst
(aaron.moss@state.co.us).

## 3. Download catch
The reader repeats OnBase's own page flow (docpop.aspx → PdfPop.aspx form post → OBToken → ViewDocumentEx → file).
It downloaded 2021, 2022 and 2023 at 11:57 on 2026-11-08 (and an earlier session 2020 and 2024); from about 12:28
OnBase answered every scripted attempt with its "Sign In" page (two different server nodes, fresh cookies, fresh app
id), while headless Chrome still downloaded 2025 anonymously at 12:30. Not understood. The reader now treats a year
that won't download as missing (`cleaning.download_failed`), never half-counted; a year downloaded once is cached
(gzip JSON, ~6 MB a year, keyed by docid so a re-issued listing is fetched again).

## 4. Placement sample (the California way)
Denver County (08031), 2024, random 2,000 of 15,501 rows (seed 2026); TIGER/Line 2024 network; `placement_sample.json`.
- GPS present and plausible: **98.5%**. Street pair given: 99.3%.
- Hidden-GPS locator test: placed **83.5% of pairs** (82.95% of all); auto under `Gate(tiger_only_auto=True)` 79.5%;
  within 250 ft of the hidden GPS **89.3% (Wilson low 87.7%)**; all placed 88.1% (low 86.5%).
- Not placed: "no intersection of the two named streets" 251 (ramps, Peña Blvd, "45TH AVE S"), streets meeting in
  more than one place 61, "missing street name" 15 ("WELTON ST & 1400 BLK").
- No-GPS crashes it would add: Denver 2024 has 364 without GPS, 361 of them with a street pair; at 83% that is about
  300 more crashes placed. Statewide the share without GPS is far larger in 2021 (24%) and 2022 (16%).
- House addresses: not a CDOT field (block numbers appear inside the street fields; shared-fixes.md #1).

## 5. Importer
`backend/crashiq/sources/co_cdot.py` (`fetch_contract`), plug-in `backend/crashiq/statepacks/co.py`
(`first_year=2021`, `final_lag_months=10`), methods `data/reference/methods_co.json`, counties
`data/reference/county_boxes_co.json` (64), test `tests/test_source_co.py` on a 16.6 KB Excel fixture of 57 live 2024
rows. Returns every crash with GPS in the box plus every no-GPS crash in the study's counties (the core filters those
by street name).

## 6. End to end (port 8102, 2026-11-08)
E Colfax Ave, Colorado Blvd to Holly St, Denver (0.98 mi, 23 study intersections), 2021-2025: the reader read 492,312
rows (13,684 no-GPS Denver crashes passed to the core); pulled 686, **counted 290**: K 4 · A 11 · B 38 · C 32 · U 0 ·
O 205. Crash cost: none (CDOT's costs not verified). 12 findings. PDF 75,373 bytes, Excel 40,504 bytes, 48 s on the
cached listings. Excluded 396: outside the buffer 177, no-GPS crashes whose cross street isn't on the corridor 168,
outside the limits 46, not on the corridor street 3, freeway 2. (`e2e_result.json`)

## What we didn't check
Why OnBase refuses scripted clients; the 2007-2020 layout; NAD / address points; CDOT's own SPFs (LOSS); the Denver
open-data crash layer (statewide covers Denver).
