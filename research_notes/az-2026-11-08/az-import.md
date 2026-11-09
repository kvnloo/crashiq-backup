# Arizona: crash data for CrashIQ (gated, no pack)

Hermes, 2026-11-08. Every number below was measured live today unless marked. Brief: `~/.hermes/states-BRIEF2.md`.

## Verdict

**Bucket D (gated), verified.** The 2026-11-02 screen was right for Arizona. ADOT's statewide crash records come only
through ACIS (an account that needs an inter-governmental agreement plus a signed NDA and acceptable-use agreement) or
a public-records request. No statewide pack is built; this folder holds the notes, a "bring your export" column map
(`az-column-map.json`) and a placement test of ADOT's location format on Tempe's open rows.

## Sources checked

| Source | Access | Years | Location | Severity | Paid-use licence |
|---|---|---|---|---|---|
| ADOT ACIS, https://adotdw.dot.state.az/ACIS | **Gated**: access form https://azdot.gov/planning/traffic-safety/acis-access-request-form needs an IGA with ADOT (or have one created via JPABranch@azdot.gov), an NCIC code, a signed NDA and AUA | statewide, current | "Crashes are geo-coded to ATIS Routes"; on road, crossing feature, offset | KABCO (incident and person) | unclear: NDA/AUA terms (https://azdot.gov/sites/default/files/2024-01/AUA-NDA.pdf; azdot.gov blocks scripted download, not read) |
| ADOT Public Record Center, https://azdot.govqa.us/WEBAPP/_rs/supporthome.aspx | **Request** (account) | per request | per request | per request | unclear |
| ADOT Crash Facts PDFs 2006-2024 and AASHTOWare dashboards, https://azdot.gov/planning/traffic-safety/arizona-motor-vehicle-crash-facts | open | 2006-2024 | aggregate only | aggregate | n/a: not record-level |
| ADOT ArcGIS Online layers (`Fatal_Crashes_2012_16`, `Serious_Injury_Crashes_2012_to_2016`, `High_Risk_and_High_Crash_Locations_`) | open | 2012-2016 | points | K / A only | unclear; stale, fatal/serious only |
| **City of Tempe** "1.08 Crash Data Report (detail)", https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/CrashDataReportforGISstory/FeatureServer/0 | open, no login | 2012-2026 (2012 4,258 ... 2019 5,366; 2020 2,280; 2021 2,805; 2022 3,745; 2023 4,544; 2024 3,980; 2025 3,261; 2026 842 so far); 59,094 rows | Latitude/Longitude on 99.95% of 2025 rows; StreetName + CrossStreet + Distance | KABCO words (Fatal ... No Injury) | **ok_with_attribution**: item licence "This work is licensed under a Creative Commons Attribution 4.0 International License", credit "City of Tempe" |
| Tucson / Phoenix | Tucson: only University of Arizona student layers (2018-2021 summaries); Phoenix open data (phoenixopendata.com) lists citations and traffic volumes, no crash table | | | | |

Tempe is one city (about 3,000-5,000 crashes a year, a small share of Arizona's; the statewide total was not read) and the brief keeps city feeds as gap
fillers for a state source, so it does not make a pack on its own.

## The export's columns

ACIS "Data Export" gives three tables, INCIDENT, UNIT and PERSON, "with all the crash fields that are entered from the
crash report", as CSV or XML; the "Standard Detail Report" (Excel/PDF/CSV/XML) is what ADOT's training uses for corridor
studies (ADOT ACIS Training Videos 1 and 3, Apr 2023, read through an extractor). ADOT publishes no column list; the
fields are the Arizona Crash Report form (Instruction Manual, 13th ed., Aug 2023). Tempe's open table is built from the
same ADOT incidents (incident ids such as 4266152) and shows the names and values to expect: StreetName, CrossStreet,
Distance, JunctionRelation, Injuryseverity, Collisionmanner, Lightcondition, Weather, SurfaceCondition, Latitude,
Longitude. Map: `az-column-map.json` (marked `verified_against_real_export: false`).

Severity (Tempe, all years): No Injury 39,894; Possible Injury 9,003; Suspected Minor Injury 4,439; Non Incapacitating
Injury 4,411 (older form wording); Incapacitating Injury 559 (older); Suspected Serious Injury 476; Fatal 181;
Unknown 130. Maps cleanly to K/A/B/C/O/U.

## Placement sample, the California way

`placement_sample.py az` (the same script serves Nevada),
output `placement_sample.json`. 2,000 random Tempe 2025 crashes; GPS hidden; placed from StreetName + CrossStreet on
TIGER/Line 2024 Maricopa (04013) EDGES + FEATNAMES clipped to Tempe; scored against the hidden GPS.

- GPS plausible: 99.95%. Street pair: 93.1%.
- Placed from names: **86.0%** of all crashes, 92.4% of pairs (unique_pair 1,702, exact 12, near 3, relaxed 2).
  Review: 142 (no intersection of the two names 79, streets meet more than once 63). No cross street: 139.
- Auto under the default `Gate()`: 0% (TIGER-only network, expected). With `Gate(tiger_only_auto=True)`: 85.7%.
- Within 250 ft of the hidden GPS: **72.7%** of placed (Wilson low 70.5%), n = 1,719. Tempe's copy has the offset
  distance but **no offset direction**, so crashes are put at the intersection. On crashes with an offset of 250 ft
  or less: **91.1%** (low 89.5%, n = 1,368). An ACIS export with the direction should close most of the gap (not
  measured).
- What breaks: landmark cross streets (`Forest Service 01 Tempe Ave`, `E Tempe Marketplace`, `S Athletes Pl`).

## Methods (rates, costs)

Not collected. ADOT's HSIP material (https://azdot.gov/sites/default/files/2019/06/hsip-presentation-021518.pdf) and
manuals sit on azdot.gov, which serves scripted downloads a bot-check page. No pack, so no `methods_az.json`.

## What the user needs to do

1. Pick one way in:
   - **ACIS account** (best: statewide, self-serve exports). Your firm needs an IGA with ADOT (ask JPABranch@azdot.gov),
     then fill https://azdot.gov/planning/traffic-safety/acis-access-request-form with the signed NDA and AUA. Read
     the AUA for whether exports may be used inside a paid tool.
   - **Public-records request**: make an account at https://azdot.govqa.us and ask for statewide incident, unit and
     person records, 2020-2024, CSV, with latitude/longitude, offset distance and direction.
2. Send Engineering one ACIS Data Export (INCIDENT/UNIT/PERSON, one county, one year) to confirm `az-column-map.json`
   and build the upload reader.
3. Optional now: Tempe's open table could be added as a city source (CC BY 4.0) once there is a statewide source to
   sit under.

## What we didn't check

The NDA/AUA text (download blocked); ADOT's HSIP manual, crash costs and rates; Mesa, Chandler, Scottsdale, Glendale
open data (ArcGIS Online search found only consultant HIN layers); Pima Association of Governments' crash data.
