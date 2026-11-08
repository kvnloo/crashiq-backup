# Indiana: "bring your export" column map (Hermes, 2026-11-08)

Indiana has no open crash records, so CrashIQ has no Indiana pack. If you get an export (AASHTOWare Safety or an
ARIES extract), this is how its columns would feed CrashIQ's crash contract (`packs.CONTRACT_KEYS`).

**Spec status:** INDOT publishes no AASHTOWare Safety export layout. The column names below are ARIES export names as
they appear in three public layers built from ARIES exports (Bloomington/Monroe County `Monroe_County_Crashes`; IMPO
`Bike_and_Ped_Crashes_22toJuly24` and `2018_2025 Fatal and SSI Crash Data`) and the VCRS data dictionary
(Indiana 2007, NHTSA copy: `MSTRRECNBRTXT` = master record number). **Confirm against your export's header row**
before a reader is written.

| CrashIQ key | ARIES / AASHTOWare column (expected) | how |
|---|---|---|
| crash_id | Master Record Number (`MSTRRECNBRTXT`) | text |
| date, year, hour | Date (or Year, Month, Day), Hour / Collision Time | ISO date; hour 0-23 |
| lat, lon | Latitude, Longitude | decimal degrees; drop 0/0 and points outside Indiana (37.7-41.8 N, 88.1-84.8 W) |
| primary_road | Roadway Name (`Reported_Location` holds "1ST & FESS") | split "A & B" |
| secondary_road | Intersecting Road / Cross Street ("W HAWTHORNE ST & S 6TH ST") | split on " & " |
| offset_ft, offset_dir | Feet From / Direction From intersection (if exported) | feet; N/S/E/W |
| city, county_fips | City, County | county name -> 18xxx FIPS (Census list) |
| severity | **Crash Severity Level (NEW)** (KABCO from 2022, INDOT B8) | K/A/B/C/O as given; older years: Injury Type / Injury Status (Fatal, Incapacitating, Non-incapacitating, Possible) -> K, then U for the rest (INDOT says A from SSI is valid only 2022 on) |
| killed, injured | Number Killed, Number Injured / Number Dead | ints |
| collision_type | Manner of Collision ("RIGHT ANGLE", "REAR END", "HEAD ON BETWEEN TWO MOTOR VEHICLES") | RIGHT ANGLE -> BROADSIDE, REAR END -> REAR END, HEAD ON... -> HEAD-ON, SIDESWIPE... -> SIDE SWIPE |
| ped, bike | Crash Type / Collision Type ("Pedestrian", "Pedalcyclist") | flags |
| lighting, weather, surface | Light Conditions, Weather Conditions, Surface Conditions | upper case; DARK (LIGHTED) -> DARK - STREET LIGHTS, DARK (NOT LIGHTED) -> DARK - NO STREET LIGHTS |
| is_freeway | Road class / Roadway Class ("Interstate") | Interstate or toll road |
| pcf (not in contract) | Primary Factor ("FAILURE TO YIELD RIGHT OF WAY") | kept as text |
| report_version, deleted, preliminary, state | none | 0, False, year >= current year, "IN" |
| motorcycle, heavy_truck, parties | unit-level table, if exported | else False / [] |

Methods ready for a pack (INDOT B8, *Indiana Crash Severity Guidelines*, 2026, `~/.hermes/state-manuals/in/`):
see `in-methods.md`.
