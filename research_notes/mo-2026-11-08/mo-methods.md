# Missouri methods (Hermes, 2026-11-08)

Downloaded to `~/.hermes/state-manuals/mo/`:
- MoDOT *Engineering Policy Guide 905.3 Transportation Impact Analysis* (saved HTML), sha256 180c025c…62c530,
  <https://epg.modot.org/index.php/905.3_Transportation_Impact_Analysis>.
- *Missouri Uniform Crash Report Preparation Manual* (SHP-2 STARS, revised 2019-01-01), sha256 e55ac78a…4b136.
- *MUCR Preparation Manual 2024-01-01*, sha256 1b247bc5…1fe (the 2024 form: suspected serious / minor / possible).

| value | Missouri | where |
|---|---|---|
| injury levels | Fatal K, Serious A, **Minor B & C**, No Injury Apparent O | EPG 905.3.6.1.4, MoDOT Injury Severity Classification table |
| crash costs | **missing**: "a dollars per crash value, based on periodic FHWA determined values and adapted to Missouri's Consumer Price Index. Contact the MoDOT project core team" | EPG 905.3.6.3.1 |
| statewide average rates | "can be obtained through MoDOT"; none published | EPG 905.3.6.1.3 |
| critical rate | statewide average + K·sqrt(average/exposure) + 1/(2·exposure), **K = 1.645 (95%)** | EPG 905.3.6.1.4 |
| study period | "the most recently available five (5) full years ... is standard"; 10 for ped/bike or rail crossings | EPG 905.3.6.1.3 |
| crash location | After / Before the intersecting road along the roadway direction, feet | MUCR 2019 p. 40-41 |

CrashIQ screens with the critical rate against the corridor's own sites at MoDOT's K = 1.645 (no Missouri statewide
averages loaded). The older MoDOT HAL Manual (3rd ed., 1999) has fatal/injury/PDO crash costs; too old to use, not loaded.
