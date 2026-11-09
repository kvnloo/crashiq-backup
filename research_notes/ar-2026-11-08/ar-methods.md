# Arkansas methods (Hermes, 2026-11-08)

Manual downloaded to `~/.hermes/state-manuals/ar/ardot_hsip_process_2022.pdf`
(sha256 bb2e15efb39a72140f8a963314b27b933351d3652eca5acda1664f7b8be6194a), from
https://fhwaapps.fhwa.dot.gov/hsipp/Questions/OpenFile/1414 (attached to ARDOT's HSIP report; FHWA's 2025 Arkansas
HSIP report says "The HSIP Process document (attached) was updated in 2022").
**ARDOT, Highway Safety Improvement Program Process, Version 2.0, 12/2022** (App. A, p. A-2: 7/2011 v1.0, 12/2022 v2.0).

| Value | ARDOT says | Where |
|---|---|---|
| Crash costs (comprehensive, per crash) | K $6,343,000 · A $335,000 · B $123,000 · C $69,000 · O $11,000; "Based on Table 4A-1 in the 2010 HSM, but adjusted for inflation specific to Arkansas" | App. E, p. E-2 (PDF p. 59) |
| Dollar year | "New Crash Cost Groupings (Adjusted for 2020 dollars)" | App. E, p. E-3 (PDF p. 60) |
| Benefit-cost groups | KA $1,406,292 · BC $88,101 · O $11,000 (weighted by 2014-2018 severity shares) | App. E, p. E-3 |
| Network screening | moving from KA Crash Rate to **Critical KA Crash Rate**, ranked by Critical Index (KA rate / critical KA rate); segments up to 5 mi; intersections ~0.03 mi (~160 ft) influence on each leg | §2.2.1, pp. 10-11 |
| SPF calibration | six SPFs calibrated (eight factors), "proved to not be useful"; none published | §2.2.1, p. 11 |
| Statewide average crash rates | not in this document (ARDOT's Traffic Safety section "computes statewide average crash rates by roadway type", https://ardot.gov/divisions/planning/traffic-safety/) | missing |
| Study period | five-year totals used for ranking (App. E, App. F); no corridor-study minimum | missing |

In `methods_ar.json`: crash costs cited and verified (sha256 recorded); screening uses the HSM critical rate against
the corridor's own sites (national method, user decision #34), with ARDOT's own method named; rates, minimum years
and SPF calibration are `missing` with the reason.

## Differences from California
- Costs: ARDOT prices every level separately (CA's table combines K and A); 2020 dollars, HSM-based, not FHWA 2025.
- Screening: ARDOT's is KA-only critical rate (CA: TASAS base rates per rate group).
- Exposure: ARDOT's rates are per HMVMT (HSIP report); CrashIQ has no Arkansas AADT, so no rates are computed.
- Intersection influence: ARDOT 160 ft per leg (CA studies in CrashIQ use the study's own radius).
