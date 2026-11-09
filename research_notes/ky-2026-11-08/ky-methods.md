# Kentucky methods (Hermes, 2026-11-08)

Manual downloaded to `~/.hermes/state-manuals/ky/`:
- KTC, *Analysis of Traffic Crash Data in Kentucky (2020-2024)* (KYTC), sha256 7a3874ed…c46c56c,
  <https://transportation.ky.gov/HighwaySafety/KYTrafficCrashAnalysis/AnalysisTrafficCrash2020-2024.pdf>.

| value | Kentucky | where |
|---|---|---|
| crash costs | **missing**: KYTC's HSIP reports price benefit/cost with the National Safety Council's comprehensive costs; no KYTC table found. The public data has no A/B/C anyway. | KYTC HSIP reports 2023-2025 (FHWA site) |
| statewide average rates | published per 100 MVM (sections) / per MEV (spots) by highway type; not loaded, CrashIQ has no Kentucky AADT | KTC 2020-2024, p. viii and rate tables |
| critical rate | Cc = Ca + K·sqrt(Ca/M) + 1/(2M), **K = 2.576 (p = 0.995)**; critical number Nc = Na + K·sqrt(Na) + 0.5 | KTC 2020-2024, p. ix (PDF p. 11) |
| HSIP screening | Kentucky SPFs (KAB, CO) + Empirical Bayes, ranked by the cost of excess expected crashes (KA/B/C/O) | FHWA case study "Kentucky's Network Screening Process"; KTC report |
| years | five-year analysis | KTC 2020-2024, Table 1 (PDF p. 20) |

Differences from California: K = 2.576 (99.5%) for the critical rate where Caltrans/HSM examples use 1.645 (95%);
Kentucky's own SPFs instead of TASAS base rates; no published per-severity cost table. CrashIQ screens with the HSM
critical rate against the corridor's own sites (national method, user decision), noted in `screening.state_method`.
