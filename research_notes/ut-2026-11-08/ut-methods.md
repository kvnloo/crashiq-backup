# Utah methods (Hermes, 2026-11-08)

Manuals in `~/.hermes/state-manuals/ut/` (sha256 in `data/reference/methods_ut.json` where used).

| Value | Utah | Source |
|---|---|---|
| Crash costs | K $15,593,700 · A $1,661,800 · B $373,500 · C $198,700 · O $17,100; KA weighted $3,904,059 (2025 $) | UDOT T&S memo "Utah's Crash Costs for Calendar Year 2026", 2026-03-16, Table 1, p. 1 (sha256 1da9527f…) |
| How costs apply | "Apply weighted crash costs when working with observed crash severities": CrashIQ prices K and A crashes each at the KA cost $3,904,059; B, C, O at their own | same memo, "Application of Severity Distributions and Crash Cost Values" 2, pp. 3-4 |
| Statewide average rates by facility type | missing: not in the memo or the HSIP manual; no Utah AADT in CrashIQ | — |
| Screening | UDOT ranks HSIP projects by B/C from crash history, statewide state-system crash models and usRAP. CrashIQ uses the HSM critical rate against the corridor's own sites | UDOT HSIP Manual, June 2025, Sec. 5.1.2.1 and 5.1.3, pp. 14-15 (sha256 ceb72d64…); HSM Ch. 4 |
| Minimum years | missing | — |
| SPF calibration | missing | — |

Also saved: UDOT's 2025 crash-cost memo (2024 $; superseded), sha256 7aafcd5f….
Differences from California: every value is UDOT's own (Caltrans's are never used). UDOT's costs are per crash and
already allow for several people hurt in one crash (memo p. 2). U is unpriced (Utah has no U rows).
