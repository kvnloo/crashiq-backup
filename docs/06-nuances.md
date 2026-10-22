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
| N10 | Collision diagram (#106): which arrow symbol stands for each CCRS movement code, and which parties get an arrow? | The diagram is drawn by code from these codes; the mapping decides what a reviewer reads into it | OPEN (user). Proposal and counts below (Engineering, 2026-10-20) |

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

## N10 proposal: collision diagram symbols (Engineering, 2026-10-20; not built, #106)

A collision diagram draws each crash at an intersection as one arrow per party, placed on the approach the party came
from, with the crash's severity at the point where they met. CCRS gives three things per party (Parties table):
- **movement before the collision:** `MovementPrecCollDescription`
- **direction of travel:** `DirectionOfTravel`, N / S / E / W
- **party type:** Driver, Pedestrian, Bicyclist, ParkedVehicle, …

Everything below is from live CCRS Parties 2024, statewide (data.ca.gov, pulled 2026-10-20): **815,978 parties**.

### Proposed symbols (standard collision-diagram arrows, as in FHWA / ITE practice)
| CCRS movement | Parties 2024 | Proposed symbol | Glyph |
|---|---|---|---|
| `PROCEEDING STRAIGHT` | 387,764 (47.5%) | Straight arrow | → |
| `STOPPED` | 88,167 (10.8%) | Stopped: short arrow ending in a bar | ⇥ |
| `SLOWING/STOPPING` | 39,757 (4.9%) | Stopped: short arrow ending in a bar | ⇥ |
| `PARKED` | 58,255 (7.1%) | Parked: small box, no arrow | ▭ |
| `MAKING LEFT TURN` | 53,489 (6.6%) | Left-turn arrow | ↰ |
| `MAKING RIGHT TURN` | 23,389 (2.9%) | Right-turn arrow | ↱ |
| `MAKING U TURN` | 5,164 (0.6%) | U-turn arrow | ↶ |
| `OTHER UNSAFE TURNING` | 27,898 (3.4%) | Turning, side not stated: bent arrow with a '?' (see question 2) | ↝? |
| `CHANGING LANES` | 33,552 (4.1%) | Lane-change arrow (offset to the next lane) | ⤳ |
| `MERGING` | 3,566 (0.4%) | Lane-change arrow | ⤳ |
| `LANE SPLITTING` | 1,335 (0.2%) | Lane-change arrow | ⤳ |
| `PASSING OTHER VEHICLE` | 4,615 (0.6%) | Lane-change arrow | ⤳ |
| `XING INTO OPPOSING LANE` | 2,947 (0.4%) | Straight arrow drawn in the opposing lane | → |
| `TRAVELLING WRONG WAY` | 2,452 (0.3%) | Straight arrow against the lane's direction, labelled 'wrong way' | ← |
| `BACKING` | 14,633 (1.8%) | Backing arrow (dashed, reversed) | ⇠ |
| `PARKING MANEUVER` | 3,173 (0.4%) | Backing arrow | ⇠ |
| `ENTERING TRAFFICD` | 8,599 (1.1%) | Entering arrow (curving in from the curb or a driveway) | ↪ |
| `RAN OFF ROAD` | 13,050 (1.6%) | Out-of-control arrow (wavy) | ↯ |
| `OTHER` | 31,055 (3.8%) | No arrow: counted under the diagram as 'movement not stated' | — |
| `(blank)` | 13,118 (1.6%) | No arrow: counted under the diagram as 'movement not stated' | — |

Symbols are drawn in the text colour (no hue). The crash's severity is a dot at the conflict point, in the existing
severity ramp: fatal and serious stand out, and the colour-blind check (#108) is unchanged.
`ENTERING TRAFFICD` is CHP's own spelling ("ENTERING TRAFFIC").

### Placement
- **Approach:** the party's direction of travel picks the leg it came from (northbound comes from the south leg).
  Each N/S/E/W is matched to the intersection's nearest leg by bearing, since legs are rarely exactly north-south.
- **No direction:** 22,875 parties in 2024 (2.8%; 10,183 of them drivers) can't be placed, so they aren't drawn and
  are counted under the diagram.
- **Pedestrians** (14,690 parties): most have no movement code (6,864 blank, 2,129 OTHER, 4,555 PROCEEDING STRAIGHT).
  Proposed: a dashed walking line across the leg, whatever the movement code; what they were doing is already in T15.
- **Bicyclists** (11,872 parties): the same arrows as vehicles, drawn thinner with a small bicycle mark.
  8,567 go straight; 662 travel the wrong way.
- **Parked vehicles** (60,080 parties; 56,297 coded PARKED): the parked box at the curb of their leg.

### Questions for the user
1. **Which symbol set?**
   - **A, the full set above:** 11 distinct symbols.
   - **B, a simpler six:** straight, left, right, U-turn or backing, lane change, stopped or parked. Ran-off-road,
     entering and wrong-way would fold into straight, and their codes would be listed in the drill-down table.
2. **`OTHER UNSAFE TURNING`** (27,898; 3.4%): CHP doesn't say which side.
   - (a) A generic turn arrow marked "?" (proposed).
   - (b) Leave it undrawn and count it.
   - Inferring the side from the collision type would be a guess, so it isn't offered.
3. **Which parties get an arrow?**
   - (a) Every party (proposed): a two-car crash shows both.
   - (b) Only the party at fault, which is simpler but hides the other driver's movement.
4. **Where the diagram shows:** per intersection in the location drill-down (#106 as written), and only for
   intersections with at least one crash.

### N10 revision: DemandIQ's diagram conventions (Engineering, 2026-10-21, after the user's note)
The user has drawn collision diagrams before and asked that CrashIQ follow the conventions already built for DemandIQ:
`demandiq/backend/line_diagram.py`, the v26-approved WSP line-diagram engine, whose geometry, colours and arrow
shapes are locked there, and `demandiq/frontend/src/components/MovementSvg.jsx`, the same arrows as SVG.
What CrashIQ would reuse as-is:

- **One square cell per intersection:**
  - grey road arms for the legs that exist only
  - a control symbol at the centre: signal = open circle; roundabout = ring with a filled centre; stop = dot plus a stop
    sign on each stopped approach
  - street names in bold along the arms, N–S rotated, wrapped at " / " and shrunk to fit
  - a number badge top-left and an "A @ B" banner top-centre
- **Arrows:** MUTCD-style right-angle polylines in one grey (`#969696`), arrowhead at the end. Four base movements:
  straight (T), left (L), right (R) and U-turn (U, a loop back toward the driver's left).
- **Approaches:** labelled by travel direction (NB, SB, EB, WB), which is exactly CCRS `DirectionOfTravel` (N/S/E/W).
  Each approach's arrows sit in its own quadrant (NB lower right, SB upper left, EB lower left, WB upper right:
  right-hand traffic), in lane order from the median outward: U, L, T, R.

What changes for crashes: **the number at each arrow is a crash count, not a traffic volume**, e.g. "12 (2 KSI)".
The counts come from a new table (approach × movement), recounted from raw rows in the golden tests.
The diagram is drawn as SVG in the drill-down and in the PDF.

Mapping CCRS movements onto the four DemandIQ arrows (Parties 2024, statewide):

| CCRS movement | Arrow |
|---|---|
| PROCEEDING STRAIGHT (387,764), XING INTO OPPOSING LANE (2,947), TRAVELLING WRONG WAY (2,452) | T |
| MAKING LEFT TURN (53,489) | L |
| MAKING RIGHT TURN (23,389) | R |
| MAKING U TURN (5,164) | U |
| STOPPED, SLOWING/STOPPING, PARKED, CHANGING LANES, MERGING, PASSING, LANE SPLITTING, BACKING, PARKING MANEUVER, ENTERING TRAFFIC, RAN OFF ROAD, OTHER UNSAFE TURNING, OTHER, blank | no arrow: a one-line "other movements" count per approach under the cell, by code, exact numbers in the table |

Revised questions for the user (they replace questions 1 and 3 above):
1. **Which party is drawn?**
   - Recommended: **the party at fault** (party 1 when none is marked). Then each crash is one arrow and the counts
     add up to the intersection's crashes, like T16.
   - The alternative, every party, makes counts add up to parties, not crashes.
2. **Four arrows plus an "other movements" line, or extra glyphs** (stopped, backing, lane change) in the same grey
   style? Recommended: the four DemandIQ arrows plus the line, since the engine is approved as it is.
3. **Also a per-crash diagram**, the traditional style where each crash's vehicles' arrows meet at a conflict point
   with a severity mark? Recommended: not now. The per-crash list is in the drill-down table; build it later if
   reviewers ask.

### N10 revision 2: standard collision-diagram symbols on DemandIQ's layout (Engineering, 2026-10-21; not built)
User direction (docs/03, 2026-10-21): DemandIQ for the **layout** only (the cell, approaches by direction of travel,
lanes laid out so nothing overlaps). The **symbols** follow standard collision-diagram practice, not DemandIQ's volume
arrows. This replaces the arrow mapping in the revision above. Mock-up on real Crenshaw data:
`design/mockups/n10-collision-diagram.png` (generator `n10_collision_diagram.py`, data `n10_crenshaw_135th.json`).

**What the references agree on.** Sources:
- **HSM** 1st ed. Ch. 5, Exhibits 5-4 (example diagram) and 5-5 (legend), adapted from ITE. Read from the public 2009
  pre-publication draft; the published figure numbering is not verified.
- **NCDOT** TEAAS collision diagram instructions.
- **Region of Peel** Appendix O collision diagrams.
- **Seattle SDOT** collision diagram legend.

They agree on:
- One arrow per vehicle, pointing in its direction of travel, on the approach where it came from; a turn bends the tail.
- Rear-end = two arrows in line; angle = two perpendicular arrows meeting; sideswipe = near-parallel arrows meeting.
- Out of control = a wavy, zig-zag or looped line; fixed object = a bracket, box or dot at the arrowhead.
- Severity marked at the impact point: **hollow circle = injury, filled circle = fatal** (NCDOT, Peel, HSM).
- Each crash labelled with date and time, often with a road-surface/light letter code.
- Not to scale; north arrow; study period.

Where they differ:
- **Property damage only:** a crossbar (Peel, PRLTAP), a hollow triangle (HSM draft), or no mark (NCDOT).
- **Night:** a filled arrowhead (NCDOT) or a letter code (HSM, Peel).
- **Pedestrian:** a dotted arrow (HSM), "P" (NCDOT, Peel), or a dashed tail with a circle (Seattle).
- **Crash IDs:** numbered with identical crashes stacked (NCDOT), or labelled with date and time (HSM, Peel).

**Proposed symbols (as in the mock-up):**

| Crash (CCRS collision type, CA 2024 statewide; movement of the party at fault) | Symbol |
|---|---|
| REAR END (123,226) | two arrows in line, the follower behind the leader |
| BROADSIDE (74,920), at-fault party not turning left | two perpendicular arrows meeting; the other party's arrow comes from its own direction of travel |
| BROADSIDE, at-fault party MAKING LEFT TURN | the left-turn arrow (bent tail) meeting the opposing arrow (T17's left-turn split) |
| HEAD-ON (18,651) | two opposed arrows meeting |
| SIDE SWIPE (92,707), both parties the same direction | two arrows converging in a "V" |
| SIDE SWIPE, opposite directions | two arrows meeting with opposed heads |
| HIT OBJECT (73,082) | arrow ending in a bracket |
| OVERTURNED (9,000) or movement RAN OFF ROAD | wavy (out of control) arrow |
| VEHICLE/PEDESTRIAN (12,813), or any pedestrian party | vehicle arrow plus a dotted pedestrian arrow, letter "P" |
| a bicyclist, e-bike or e-scooter party | vehicle arrow plus the rider's arrow, letter "B" |
| movement BACKING | arrow with three heads (HSM "backing") |
| hit a parked vehicle, no other moving vehicle | arrow into a box with an X (Seattle "parked") |
| OTHER (11,492), not stated (1,280) | plain arrow with "?" |

**Marks on every crash:**
- **Severity at the impact point:**
  - fatal = filled circle (in the fatal colour)
  - injury = hollow circle whose ring takes the KABCO ramp colour (A orange, B yellow, C teal, U grey), so colour adds
    detail but black-and-white print still reads
  - property damage only = crossbar (Peel and PRLTAP; more legible than HSM's small triangle)
- **Light:** arrowheads hollow by day and filled in the dark (NCDOT). The crash list also gives HSM's two-letter
  surface + light code (C/W/S/O + D/N/L).
- **Number:** a small number by each crash, keyed to a list beside the diagram (date, 24-hour time, approach, type,
  severity, code). The numbers follow date order, as in NCDOT.

**Layout (DemandIQ):**
- The cell holds grey arms, the control symbol (signal circle, stop signs) and street names on the arms.
- Each crash is drawn on the approach of the party at fault, in that approach's quadrant (NB lower right, SB upper
  left, EB lower left, WB upper right).
- Fixed slots fill outward from the centre, so no two crashes overlap.
- The data comes from CCRS `DirectionOfTravel`, `MovementPrecCollDescription`, `IsAtFault` and the collision type,
  all in the pull already.

**Questions for the user:**
1. **Property damage only:** a crossbar (proposed), HSM's hollow triangle, or no mark?
2. **Night:** a filled arrowhead plus the code (proposed), or the code only?
3. **Busy intersections** (40+ crashes): stack identical crashes as one symbol with a count, NCDOT style; or split
   the diagram by period (e.g. last 3 years); or keep every crash and let the cell grow (the mock-up's 32 fit)?
4. **Where it shows:** the location drill-down and the PDF, one diagram per study intersection (as #106).

