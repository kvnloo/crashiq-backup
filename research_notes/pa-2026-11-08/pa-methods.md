# Pennsylvania methods (rates, costs, screening), 2026-11-08

Files in `~/.hermes/state-manuals/pa/`.

| Value | Pennsylvania | Source | In CrashIQ |
|---|---|---|---|
| Crash costs per crash (max severity) | K $15,327,533 · A $874,868 · B $280,486 · C $155,850 · O $14,505 (2025 $) | 2025 Pennsylvania Crash Facts and Statistics, p. 8 (PDF p. 10), "Comprehensive Loss ... Average Cost" (`crash_facts_2025.pdf`, sha256 122e3cba…) | used, `verified: true` |
| U (injury, unknown severity) | priced at the C cost | Pub 638 (2024) Table 4-3, p. 4-9: "Possible Injury and Unknown Severity" one cost | left unpriced: the core can't price U at C per state yet (shared-fixes.md item 1) |
| Cost updates | yearly in the Crash Facts book; use the newest | Pub 638 §4.8, p. 4-8 | — |
| Statewide average rates | given on request by PennDOT HSTOD (CDART Homogeneous Report) | Pub 638 §5.2.3, p. 5-12 | missing |
| Screening | PSI / excess crash cost from PA regionalized SPFs + Empirical Bayes; crash rates only at the District's direction | Pub 638 §5.2.2, pp. 5-9 to 5-10; §5.2.3 p. 5-11 | HSM critical rate against the corridor's own sites (national method, user decision) |
| Study period | "generally 3-5 years" | Pub 638 §5.2.3, p. 5-11 (Eqn. 5-3, 5-4) | `verified: false` (a rate formula's note, not a stated minimum) |
| SPF calibration | district factors | Pub 638A (2021) | missing (no SPF engine) |

Differences from California: one cost per crash by max severity, every location type (no KA pooling, no location
split); PennDOT's screening is SPF/EB based, not rate-group based.
