# North Dakota crash data for CrashIQ (Hermes, 2026-11-08)

**Bucket A\* (open, one catch), status `active`.** The 2026-11-02 screen called North Dakota gated (D, "records request"). That was wrong: NDDOT's crash records are on a public ArcGIS layer, hosted by NDSU's DOT Support Center (Upper Great Plains Transportation Institute) for NDDOT's crash dashboards.

## 1. Source (verified live 2026-11-08)

- Layer: `https://dotsc.ugpti.ndsu.edu:6443/arcgis/rest/services/NDDOT_crash/ALL_CRASHES_2017_to_2025/FeatureServer/0` ("All Crash Data - 2017 to 2025"), 104,008 crashes, `returnCountOnly`, no login.
- Found by searching ArcGIS Online for crash items by owner: NDSU's web map "North Dakota Recent Crashes" (item 17f88a574b9249ec9914fee198dda560) pointed at `dotsc.ugpti.ndsu.edu:6443/.../NDDOT_crash/`, whose folder lists six crash services.
- Columns: `crashid` (e.g. `ID1155269`), `Crash_Date` (MM/DD/YYYY), `crshr` (hour; 24 and `6-` occur on 7 rows), `Crash_Severity_KABCO` (`K-Fatal Injury` ... `O-No Apparent Injury`), `latitude`/`longitude`, `county`, `FIPS` (5-digit), `Crash_City`, `Manner_Crash`, `First_Harmful_Event`, light, weather, surface, `No_Fatalities`, `No_Nonfatally_Injured_Persons`, and NDDOT flags (`pedcrs`, `bikcrs`, `mcyclecrs`, `trckcrs`, `interstate`, `intersec`, `Rural`, `ldpcrs`, `spdcrs`, `distcrs`, `impcrs` ...). **No street names, no person or vehicle table.**
- Rows per year: 2017 15,114, 2018 14,986, 2019 14,324, 2020 8,949, 2021 9,683, 2022 10,798, 2023 10,549, 2024 9,803, 2025 9,802.
- Against NDDOT's Crash Summary 2024 (p. 6): 2024 9,803 = 9,803; other years within 2% (2017 15,114 vs 15,280; 2020 8,949 vs 8,820): the layer is the full reportable set, not a filtered copy.
- Points: every row inside North Dakota (a query for null, 0 or out-of-state points returns 0).
- KABCO 2017-2025: K 825, A 3,040, B 13,424, C 9,419, O 77,300 (crash level).
- Reporting threshold rose from $1,000 to $4,000 property damage on 1 Aug 2019 (Crash Summary 2024, p. 3): the 2020 drop is mostly that, plus COVID.
- Other services in the folder (not used): `ND_Crash_All` (live to 2026-11-05, 85,354 rows; 2024 = 12,032, more than NDDOT's reportable count), `ND_Recent_Crashes` (Injury / Non-Injury only), `Rural_Crashes_2017_to_2025`, `nddot_crash_history`.

## 2. Licence

- The layer and service have no description, copyright or licence. The dashboard item "ND County Crash Dashboard" says "historical crash information provided by the NDDOT"; licence blank. UGPTI lists it at https://www.ugpti.org/dotsc/resources/.
- NDDOT Traffic Operations Manual (January 2026, p. 19): consultants get crash data by email request, pledging "I recognize this crash data is considered to be exempted from disclosure pursuant to 23 USC § 407, and can be used only with the understanding that the City of X or its agents will not release or transfer it". That pledge covers data NDDOT sends on request; the public layer carries no such notice.
- Verdict: **unclear for paid use.** Pack is `active` on the same footing as WA, OR and AR (open, no licence). The user decides; it's a one-line flip to `reader_only`.

## 3. Placement

GPS on 100% of crashes. No street names or addresses, so the hidden-GPS street-name test can't run: **not measured**. Nothing to rescue (no crash lacks a point).

## 4. Reader and pack

- `backend/crashiq/sources/nd_nddot.py`: `fetch_contract` queries the layer by year and box (object-id paging, 2,000 per page), caches by query hash. Severity from `Crash_Severity_KABCO` (numeric id as fallback), `is_freeway` from `interstate`, crash type from manner (first harmful event for non-collisions).
- `backend/crashiq/statepacks/nd.py`: `first_year` 2017, default window 2020-2024 on 2026-11-08.
- Tests: `tests/test_source_nd.py` on `tests/fixtures/nd_nddot_sample.json` (38 live rows, 25 KB).

## 5. End to end (port 8103, 2026-11-08)

13th Avenue South, Fargo, 45th St S to 25th St S, 1.95 mi (line from Overpass way geometry), 2020-2024: pulled 677, **counted 500**: K 2, A 13, B 105, C 108, O 272. Excluded 177 (89 outside the buffer, 59 freeway crashes at the I-29 interchange, 29 outside the limits). No cost total (NDDOT has no costs). PDF 72,833 B, Excel 40,353 B, 10 findings shown.

## 6. Methods

See `nd-methods.md`. Costs: missing. Statewide rates: missing. Minimum years: 3 urban / 5 rural (TOM p. 19).

## What we didn't check

The licence with NDDOT; the `ND_Crash_All` live view's extra rows; city open data in Fargo/Grand Forks (none found on ArcGIS Online beyond consultant project layers).
