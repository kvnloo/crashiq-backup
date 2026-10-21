# CrashIQ — technical nuances list

Every doubt about crash-analysis practice goes here. The user answers from experience, or we research it.
Status: OPEN / ANSWERED (who, date) / RESEARCHED (source).

| # | Question | Why it matters | Status |
|---|---|---|---|
| N1 | One count per crash: confirm CCRS Crashes table has one row per crash (CollisionId) and that severity = most severe injury in that crash (from InjuredWitnessPassengers) | HSIP counts once per crash, not per vehicle/victim | OPEN (verify in data) |
| N2 | Does CCRS include property-damage-only (PDO) crashes? TIMS excludes them | HSIP Analyzer has a PDO cost; rates and profiles change | RESEARCHED (Hermes, 2026-10-18): yes. 58.7% of CCRS 2024 crashes have no one killed or injured (city streets 52%, freeways 66%). TIMS states it excludes PDO. See #18 report |
| N3 | Mapping CCRS injury codes to KABCO / HSIP five levels (Fatal, Severe, Other visible, Complaint of pain, PDO) | Severity counts and B/C | ANSWERED (user, 2026-10-19): old and new wording are the same K/A/B/C/O levels, no report note. docs/03 |
| N4 | HSIP influence area: 250 ft, but only to mid-block when the next intersection is < 500 ft away | Crash assignment | RESEARCHED (Caltrans HSIP instructions; see research notes) |
| N5 | COVID years 2020–2022: exclude by default in HSIP mode, or offer a toggle? | HSIP allows exclusion | OPEN (user) |
| N6 | Preliminary (most recent) CCRS records: include or not, per mode? | Data completeness | OPEN (user) |
| N7 | Grade separation: a road passing over or under the corridor (interchange, overcrossing, undercrossing) sits inside the buffer but never meets the corridor at grade. Its crashes, and interchange crashes on a freeway corridor, must not be counted | The 2D buffer and the 30 m "near" rule in `locate.py` can't tell levels apart, so these crashes leak in | ANSWERED (user, 2026-10-18): exclude them; only at-grade intersections the corridor passes through count. Detection: #67 |
| N8 | Crashes that can't be placed from any source (no GPS, cross street NOT STATED, no other source with a location): count them in the corridor's totals (crashes per mile, severity mix) without assigning them to any location, or leave them out of all counts? | Corridor totals vs location totals; hidden undercount if left out | OPEN (user). Until decided they stay on the review list labelled "on this corridor, location unknown". Other sources first: TIMS and city open data, measured in #88, terms in #126 |
| N9 | E-scooters and e-bikes: show them as their own road users on tab 3 (next to pedestrians, bicyclists, motorcyclists), fold e-bikes into bicyclists, or leave as is? | CCRS codes them, but today an e-scooter crash is in no road-user group, and an e-bike is a bicyclist only when CHP also typed the party as one | OPEN (user). Proposal and counts below (Engineering, 2026-10-20, from #139) |

## N9 proposal: e-scooters and e-bikes (Engineering, 2026-10-20; not built)

CCRS Parties carries the vehicle type in `Vehicle1TypeDesc`. Live counts, statewide (data.ca.gov, pulled 2026-10-20):

| CCRS code | What it is | Party type CHP used | 2023 parties | 2024 parties | 2024 crashes |
|---|---|---|---|---|---|
| `GoPedZipElectricScooterAndMotorboard` | stand-up e-scooter (and motorized board) | Driver 863, Other 271, other 8 | 768 | 1,142 | 1,137 |
| `ElectricBicycles` | e-bike | **Bicyclist 913**, Other 69, Driver 17 | 559 | 999 | 979 |
| `ElectricallyMotorizedBoards` | e-skateboard | Other 17, Driver 3 | 20 | 20 | 20 |
| `MotorizedBicycle` | moped-style motorized bicycle | Driver 203, other 17 | 155 | 220 | 215 |
| `MotorDrivenCycleScooter15HpOrLess` | motor-driven cycle / scooter ≤ 15 hp | Driver 1,066, other 167 | 955 | 1,233 | 1,222 |
| (for scale) `Bicycle` | pedal bicycle | Bicyclist 10,758 | 9,852 | 10,773 | 10,583 |

How the app counts them today (`ca_ccrs.mode_flags`):
- **E-bikes:** counted as bicyclists when CHP typed the party `Bicyclist` (913 of 999 in 2024). The other 86 are in no group.
- **E-scooters and e-boards:** in no group. They aren't typed `Pedestrian` or `Bicyclist`, and the motorcycle words don't match the code.
- **Motorized bicycles and ≤ 15 hp motor-driven cycles:** in no group either.

E-scooter parties grew 49% from 2023 to 2024; e-bikes 79%.

Options for the user:
- **A. Own row:** "E-scooters and e-bikes" next to pedestrians, bicyclists and motorcyclists in T19, the ranking, and the strip and map ring. The headline would stay pedestrians + bicyclists.
- **B. Fold in:** e-bikes into bicyclists whatever the party type; e-scooters as their own row.
- **C. Leave as is:** CHP's party type decides.

Whichever is chosen, `MotorizedBicycle` and `MotorDrivenCycleScooter15HpOrLess` need a call too: count them with motorcycles, or leave them out.

