# Delaware methods (rates, costs, screening), 2026-11-08

Files in `~/.hermes/state-manuals/de/`.

| Value | Delaware | Source | In CrashIQ |
|---|---|---|---|
| Crash costs | none published: DelDOT "began development of Delaware-specific crash costs using FHWA values as a guide" and plans to complete them in 2026 | Delaware HSIP 2025 Annual Report (FHWA site; download refused, read via search extract, page not recorded) | missing |
| Statewide average rates | none published | — | missing |
| Screening | Hazard Elimination Program: 3-year crash history; segments by crash rate on a 0.1-mile sliding window; intersections by frequency and severity | DelDOT HSIP presentation, Highway Safety Summit, 2024-04-17, PDF p. 9 (`deldot_hsip_summit.pdf`, sha256 d34f741e…) | HSM critical rate against the corridor's own sites (national method, user decision) |
| Crashes counted | fatal, personal injury and PDO (non-reportable out) | same, PDF p. 18 (HRRR: "five fatal, personal injury, and/or property damage only crashes during a three-year period") | reader leaves non-reportable out |
| Minimum years | 3 (HEP's window) | same, PDF p. 9 | `verified: false`: a screening window, not a corridor-study minimum |
| SPF calibration | in development (HSIP 2025) | — | missing |

Differences from California: no injury levels (K/U/O), no cost table, no rate groups.
