# Kansas methods (Hermes, 2026-11-08)

Manuals in `~/.hermes/state-manuals/ks/`: `KS_2023_Crash_Facts_Book.pdf` (sha256 674e0302…fb50), `KS_HSIP_Report_2025.txt` (text of the FHWA-hosted PDF, which refuses scripted downloads), `facts2023.txt`.

| Value | Kansas | Source | In CrashIQ |
|---|---|---|---|
| Crash costs | **Per person**: K $14,029,605, A (disabling) $774,356, B (non-disabling) $248,477, C (possible) $141,166 added per injured person; PDO crash $11,900. 2019 dollars, from FHWA-SA-17-01 adjusted to Kansas | 2023 Kansas Traffic Crash Facts, Definitions "Crash Costs", p. 77 (PDF p. 81) | `crash_costs` **missing** (CrashIQ prices one cost per crash level); the figures are kept as `person_costs` (cited, unused). Fix: `shared-fixes.md` |
| Statewide average rates | All public roads only: 187.95 crashes, 43.4 injury crashes, 1.11 fatal crashes per 100 million VMT (2023) | Crash Facts 2023 p. 1 summary | `missing` (not by facility type; no Kansas AADT in CrashIQ) |
| Screening | Crash frequency, crash rate, critical rate, EPDO, excess expected with EB, LOSS | 2025 KS HSIP report, Intersection program, pp. 8-9 | HSM critical rate against the corridor's own sites (national, decided); KDOT's method named, not built |
| Minimum years | not found | — | `missing` |
| SPF calibration | KDOT has its own calibration factors and SPFs, not published | Kansas Register 2026-05-07, RFP 106-P-1815-27 | `missing` |

Exposure unit: per 100 million vehicle miles (Crash Facts).

## Differences from California
- Costs are per injured person, not per crash, and K is not merged with A (CA's LRSM prices K and A together per crash).
- No facility-type base rates (CA has TASAS rate groups).
- KDOT's A is "disabling injury", B "non-incapacitating", C "possible": same KABCO letters, older wording.
