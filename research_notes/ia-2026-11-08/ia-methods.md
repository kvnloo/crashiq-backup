# Iowa: study methods (Hermes, 2026-11-08)

Manuals in `~/.hermes/state-manuals/ia/` (sha256 in `data/reference/methods_ia.json`).

## §1 Crash costs: Iowa TSIP Benefit Cost Ratio Worksheet
`tsipB-C.xlsm` (Iowa DOT Office of Traffic and Safety, https://ia.iowadot.gov/traffic/tsip/tsipB-C.xlsm, saved
2022-05-20), sheet 'Reference Lists' D7:D11 (Crash Costs), C2 (Year of Crash Cost Data: 2018):

| level | cost (2018 $) |
|---|---|
| K (fatal) | 3,253,349 |
| A (major injury) | 3,253,349 |
| B (minor injury) | 217,607 |
| C (possible/unknown injury) | 102,564 |
| O (property damage) | 12,656 |

- Iowa prices K and A the same (its combined fatal and serious injury cost), one cost per level for every location.
- Iowa's C cost covers "Possible/Unknown Injury"; CrashIQ leaves U unpriced (shared rule) and counts it.
- The worksheet escalates at 4% a year (sheet 'Benefit Cost Worksheet' D6); CrashIQ prints the 2018 values.

## §2 Minimum years: Data Driven Safety Guidance
Iowa DOT Data Driven Safety Guidance (Version 1.0, October 18, 2017), §2.2.1, printed p. 6 (PDF p. 10): "the Iowa
DOT recommends the analysis use the most recent five years… a minimum of three years". Value 5, minimum 3.

## §3 Statewide rates and SPFs: missing
- Statewide crash averages: the Guidance (§4.1.4, printed p. 21, PDF p. 25) links a web page,
  www.iowadot.gov/crashanalysis/comparablesprofilesmain.htm, HTTP 404 on 2026-11-08. CrashIQ also has no Iowa AADT.
- SPF calibration: the Guidance's Tables 3-1 and 3-2 (printed p. 13, PDF p. 17) publish Iowa freeway and rural
  two-lane calibration factors; not loaded (CrashIQ has no SPF engine).

## §4 Screening: HSM critical rate (national), Iowa's method noted
Iowa DOT screens with its SPF-based Potential for Crash Reduction (PCR) tool (Iowa HSIP 2025 report). Not built;
CrashIQ uses the HSM critical rate against the corridor's own sites (HSM 1st ed., Ch. 4, Sec. 4.2.3).
