# California: TIMS (Transportation Injury Mapping System), UC Berkeley SafeTREC

**Where:** https://tims.berkeley.edu. Free account (approved instantly). SWITRS Query & Map exports Crashes / Parties /
Victims CSV per query. Last 10 final years + provisional years. Updated quarterly from CHP extracts.
**What it is:** CHP's SWITRS/CCRS records plus SafeTREC's geocode. Not an independent record source.
**Licence:** no licence grant. Terms (about.php#terms): acknowledge "Transportation Injury Mapping System (TIMS), Safe
Transportation Research and Education Center, University of California, Berkeley"; data "AS IS"; §409 notice; may not be
used in connection with pending litigation against the State or a local authority (CPRA); Caltrans staff told not to rely on
it for engineering decisions. Commercial use isn't addressed: ask tims_info@berkeley.edu in writing before any product use.

## Fields that matter
`CASE_ID`, `local_report_number`, `PRIMARY_RD`, `SECONDARY_RD`, `DISTANCE`, `DIRECTION`, `INTERSECTION`, `STATE_HWY_IND`,
`COLLISION_SEVERITY` (1 fatal, 2 serious, 3 minor, 4 possible, 0 PDO "not included on TIMS"), `LATITUDE`/`LONGITUDE`
(officer GPS) and `POINT_X`/`POINT_Y` (SafeTREC geocode, WGS84). Codebook: /help/crashdata/switrs-codebook.php.

## Quirks (with evidence)
- **No PDO.** "TIMS excludes property-damage-only crashes." In CCRS 2024, 52% of city-street crashes and 66% of freeway
  crashes are PDO. (2026-10-18)
- **~97% of F+I crashes geocoded** (SafeTREC's figure, a rate not an accuracy). Method: Esri StreetMap Premium intersection
  locator on PRIMARY/SECONDARY ROAD + COUNTY + CITY, then the officer's offset; state highways by Caltrans TSN postmile.
  Officer GPS used only when their workflow fails. This is the same idea as our locator.
- Since CHP moved to CCRS (2015), CCRS no longer returns Caltrans highway attributes (route/postmile) to SWITRS, so
  SafeTREC now checks officer GPS on state highways and uses postmiles as the fallback.
- Query & Map counts include ungeocoded crashes; the GIS Map shows only geocoded ones.
- CHP finalizes a year 12–18 months late; provisional years grow over time.
- Join key to CCRS not tested: `CASE_ID` vs CCRS `Collision Id`, or `local_report_number` vs `Report Number`. UNVERIFIED.
