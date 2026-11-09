# Maine methods (MaineDOT manuals), 2026-11-08

Manuals are in `~/.hermes/state-manuals/me/`.

| Value | Maine says | Source | In methods_me.json |
|---|---|---|---|
| Minimum years | "the most recent 3-year period" for a crash inventory | 17-229 Ch. 305 (Traffic Movement Permits rule, 229c305-22), Part 6 Sec. 2, page 18 (sha256 c4277042…) | `min_years` 3, verified |
| Screening | High Crash Location = "eight (8) or more crashes … over the most recent three (3) year period, and the Critical Rate Factor is greater than one (1.0)" | Ch. 305, Part 6 Sec. 2 A, page 18; CRF defined page 3 ("ratio of the actual crash rate … to the statistically calculated critical rate") | `screening.state_method`; the engine stays the HSM critical rate (national, decided) |
| Network screening | HSM excess expected crash frequency with EB, for intersections, weighted by excess crash costs; K+A Potential tool for rural intersections | MaineDOT HSIP 2025 annual report (FHWA site, text read via web_extract; PDF download refused, HTTP 403) | not loaded (no SPF engine) |
| Crash unit costs | not published in a MaineDOT safety manual. Grant BCAs (`FY 2026 BCA Calculation.xlsx`) use USDOT BCA Guidance values (2024 $: K 13,700,000, A 1,302,300, B 256,300, C 122,400, O 5,500, U 238,500) | maine.gov grant BCA files, found in search, not downloaded | `crash_costs` **missing**: needs the user's decision on USDOT values |
| Statewide average rates | MaineDOT computes critical rates per location type; no published table found | — | `statewide_rates` missing |
| SPF calibration | not published | — | missing |

Differences from California: Maine screens by the Critical Rate Factor (CRF > 1, 8+ crashes in 3 years), not by TASAS base rates. There are no published KABCO unit costs, where California has the LRSM table.
