# Ohio methods (data/reference/methods_oh.json)

Manual saved: `~/.hermes/state-manuals/oh/CrashCostsUpdate.pdf` (ODOT, "Crash Costs for Highway Safety Analysis",
Year 2025, updated 5/5/26, 2 pages, sha256 f18cc067…316f), from
https://dam.assets.ohio.gov/image/upload/transportation.ohio.gov/safety/highway-safety/Crash-Analysis-Tools/ecat/CrashCostsUpdate.pdf

| Value | Ohio | Source |
|---|---|---|
| Crash costs, per crash (2025 $) | K 2,266,992; A 202,748; B 76,258; C 51,688; O 11,648 | p. 1, Economic Unit Cost column; p. 2, "Historical ODOT Published Crash Costs, Economic Unit Costs", 2025 row |
| Comprehensive (not used) | K 7,826,751.60; A 413,203.20; B 150,903.20; C 84,886.00; O 13,660.00 | p. 1, Comprehensive Unit Cost (MUWE) |
| Statewide average rates | not found | — |
| Screening | HSM critical rate against own sites (national, decided) | ODOT itself: AASHTOWare Safety (HSM Part B) since 2024; HSM Part C for HSIP apps (FHWA Ohio HSIP 2024 report; PDF 403s scripted downloads, not saved) |
| Minimum years | not found for corridor studies | HSIP threshold: 3 crashes/yr over 3 years, 30% F+I (FHWA HSIP 2024 report) |
| SPF calibration | not found (inside AASHTOWare, login) | — |

Why economic, not comprehensive: p. 2 titles the economic series "Historical ODOT Published Crash Costs", and
AASHTOWare Safety's Ohio defaults are economic too (B $74,163, C $50,268, O $11,328 = the 2024 economic row;
support.numetric.com, "Ohio DOT - Crash Injury Severity (KABCO) Costs", 2025-05-01).

Differences from California:
- The costs are ODOT's economic costs, not Caltrans' comprehensive costs.
- There are no statewide base rates (Caltrans has TASAS).
- ODOT screens with HSM Part B in AASHTOWare.
