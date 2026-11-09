# Illinois methods (Hermes, 2026-11-08)

Manuals downloaded to `~/.hermes/state-manuals/il/`:
- IDOT, *Safety Engineering Policy Memorandum Safety 1-06, HSIP* (effective Nov 1, 2006), sha256 abb5c9c3…b8e0e467,
  <https://idot.illinois.gov/content/dam/soi/en/web/idot/documents/transportation-system/manuals-guides-and-handbooks/safety/safety-1.06---safety-engineering-policy-memorandum.pdf>
- IDOT, *2024 Illinois Crash Facts & Statistics*, sha256 07ca96614c4b…bc8b8e.
- IDOT, *Illinois Traffic Crash Report SR 1050 Instruction Manual* (2019), sha256 179459599cb8…364031 (field meanings).
- IDOT, Circular Letter 2026-09 (2025 crash data availability, Aug 24 2026).

| value | Illinois | where |
|---|---|---|
| crash costs | **missing**. Per person, not per crash: fatality $2,009,575, A $171,925, B $45,300, C $27,795; PDO crash $6,485 (NSC 2024). Per-crash table only for 1999-2003, "reference only". | Crash Facts 2024 p. 23; Safety 1-06 p. 225 |
| statewide average rates | **missing**: only fatal / A-injury crashes per 100 centerline miles for rural collectors and locals (HRRR); no per-VMT table; no IL AADT in CrashIQ | Safety 1-06 p. 7 |
| screening | IDOT: peer groups with frequency, rate and EPDO critical values; 5% report. CrashIQ: HSM critical rate on the corridor's own sites (national, user decision) | Safety 1-06 p. 252 (candidate form) |
| minimum years | **5** ("five years of crash data should be used for the analysis"; "a minimum of 5 most recent years") | Safety 1-06 p. 8, p. 7 |
| SPF calibration | missing (not in Safety 1-06; no SPF engine) | |

Differences from California: five years, not three; IDOT's costs are NSC per-person estimates (no per-crash
KABCO table like Caltrans'), so CrashIQ shows no cost column for Illinois.
