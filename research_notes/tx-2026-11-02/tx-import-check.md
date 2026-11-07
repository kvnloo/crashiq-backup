# Texas import check (Hermes, 2026-11-02)

## CRIS Public Extract (TxDOT) - the source
- Spec: https://www.txdot.gov/content/dam/docs/division/trf/crash-records/public-extract-file-specification.xlsx (dated 06/13/25; "2018 and Greater"). Guide: https://www.txdot.gov/content/dam/docs/division/trf/crash-records/cris-guide.pdf
- Access: free **self-registration, open to the public** (guide §4 "Public Interface"); request by date range, CSV files in a password-protected zip. Years 2014 to current (10 years + current). Account auto-deleted after 30 days without login.
- Files: crash, unit, person, primaryperson, charges, damages, endorsements, restrictions, lookups. **`Crash_ID` links every file** (unlike NY).
- Location fields on the crash row:
  - Officer-reported: `Rpt_Latitude`/`Rpt_Longitude`, street prefix/name/suffix + block number, intersecting street (`Rpt_Sec_*`), `At_Intrsct_Fl`, offset distance + unit + direction from intersection or reference marker, `Rpt_Ref_Mark_Nbr`.
  - TxDOT locator (system-generated): `Latitude`/`Longitude`, `Located_Fl`, `Street_Name`/`Street_Nbr`, `Hwy_Sys`/`Hwy_Nbr`, `Control`/`Section`/`Milepoint`, `Dfo` (distance from highway origin), `Ref_Mark_Nbr`/`Ref_Mark_Displ`, secondary road equivalents, `Onsys_Fl`.
- Severity: KABCO. `Crash_Sev_ID` 4 fatal (K), 1 suspected serious (A), 2 suspected minor (B), 3 possible (C), 5 not injured (O), 0 unknown; same codes per person (`Prsn_Injry_Sev_ID`). Crash-row counts too (Death_Cnt, Sus_Serious_Injry_Cnt, ...). Labels changed to MMUCC wording 2018-01-01.
- Appended road inventory **for on-system crashes**: `Adt_Curnt_Amt`/`Adt_Curnt_Year` (AADT), truck %, lanes, shoulder/median widths, curve data, functional system, rural/urban, bridge and rail-crossing fields.
- Also: `Txdot_Rptable_Fl` ($1,000 rule), `Private_Dr_Fl`, `Intrsct_Relat_ID`, `Road_Part_Adj_ID`, `FHE_Collsn_ID`, contributing factors (unit file), PBCAT ped/bike codes.

## Not yet measured
- Statewide share of crashes with locator coordinates (`Located_Fl`). Austin's CRIS-derived open data (y2wy-tgr5) is 100% GPS 2021-2026 (13,201 / 13,660 / 13,035 / 12,080 / 12,012 / 8,323), but that set is filtered by location, so it says nothing about statewide.
- Licence for showing extract rows inside a paid product: no licence found; CRIS disclaimer only ("conclusions are your own"). Ask TxDOT TRF.
- Off-system AADT: STARS II / TxDOT open data (not checked today).
