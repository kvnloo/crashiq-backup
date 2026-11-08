# Connecticut methods (rates, costs, screening), 2026-11-08

Manual kept in `~/.hermes/state-manuals/ct/ctdot-hsip-implementation-plan.pdf` (sha256 484028ef...63c4; text in `hsip.txt`).
Source: CTDOT, Highway Safety Improvement Program Implementation Plan FY2027,
<https://portal.ct.gov/dot/-/media/dot/traffic-design/safety/highway-safety-improvement-plan.pdf>.

| Value | Connecticut | Source | In CrashIQ |
|---|---|---|---|
| Crash costs per crash | K $6,415,389 · A $338,576 · B $123,646 · C $69,541 · O $11,186 (comprehensive, EPDO) | HSIP FY2027 Appendix A, Table A-2 "EPDO Crash Costs by Severity", p. A-19 (PDF p. 69); same table B-2, C-4 | `verified: true`, printed and cited. U unpriced. Dollar year not stated. |
| Statewide average crash rates | used inside CRSMS ("weighted average crash rate (statewide in this instance)", p. A-20) but no table published | HSIP FY2027 | missing |
| Screening | CRSMS: excess expected crash frequency with SPFs, LOSS, EPDO average frequency, critical crash rate (Table A-1, p. A-15) | HSIP FY2027 | HSM critical rate against the corridor's own sites (national method, user's decision) |
| Minimum years | 5 years screened (2020-2024), no minimum stated | HSIP FY2027 | missing |
| SPF calibration | Connecticut SPFs inside CRSMS; no table | HSIP FY2027 | missing |

Differences from California: costs are one per KABCO level (no location-type split); no published base-rate tables.
