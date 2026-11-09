# Hawaii methods (HDOT), checked 2026-11-08

No pack, so no `methods_hi.json`. What HDOT's own documents say, for when SHACA data arrives.

| Item | Value | Source | Verified |
|---|---|---|---|
| Network screening | Number-Rate (N-R) method: "establishes a minimum crash frequency and accounts for exposure" | HSIP (Hawaii) 2025 Annual Report, FHWA, https://highways.dot.gov/sites/fhwa.dot.gov/files/2026-09/HAWAII_HSIP%20REPORT_2025(REV)_508.pdf (page not recorded: text via web extract) | no (FHWA host 403s scripted downloads; no sha256) |
| Screening windows | intersections on state roads: a minimum criteria for a 3-year period; non-intersections: sliding 0.3-mile segments, 3-year period | same | no |
| Crash costs | "crash costs established by FHWA" (no HDOT table) | same | no; needs the user's decision to use FHWA's national costs |
| Crashes analysed | "fatal and serious injury crashes for all analyses along with the total number of major traffic crashes" | same | no |
| Crash rates by facility | missing: no HDOT statewide average crash-rate table found | | |
| Critical-rate method | missing: N-R thresholds not published | | |
| SPF calibration | missing: HDOT "is working on implementing HSM Predictive Methodology" (HSIP 2025) | | |

Differences from California: HDOT screens with N-R on 3-year windows and 0.3-mile sliding segments (Caltrans uses
TASAS base rates); costs are FHWA's, not a state table.

Manuals folder `~/.hermes/state-manuals/hi/` is empty: the HSIP report is on highways.dot.gov, which returns 403 to
scripted downloads. Save it from a browser to verify the values above.
