# Indiana methods (Hermes, 2026-11-08), for a future pack

Downloaded to `~/.hermes/state-manuals/in/`:
- INDOT Traffic Engineering Manual B8, *Indiana Crash Severity Guidelines* (memo, May 2026),
  <https://www.in.gov/indot/files/Indiana-Crash-Severity-Guidelines.pdf>,
  sha256 360c1d699e3ccdc08ae73a39f0d3af63de7eb71a3f767f9f772a3d784200c6d0.
- INDOT B5, *Local Government HSIP Guidelines*, sha256 9004099f13d3…8d892e (older Index of Crash Cost method).

| value | Indiana | where |
|---|---|---|
| crash costs per crash (2025 $) | K $857,956 (= A, on purpose), A $857,956, B $212,262, C $125,600, O $15,587; "based on the severity level for the crash as a whole" | B8 p. 5 |
| KABCO | K killed; A Suspected Serious Injury (8 MMUCC injury natures); B incapacitating or non-incapacitating; C possible, refused, not reported, unknown; O none | B8 p. 3 |
| SSI years | A (SSI) valid only from 2022 (2022-2023 incomplete, ARIES 5); method in force Oct 1, 2026 | B8 p. 2, p. 4 |
| minimum years | 5 ("Going forward, 5 years of data will be used"; was 3) | B8 p. 5 |
| statewide rates, screening | not found public (AASHTOWare Safety network screening, login) | |

Note for the reader: INDOT's C level includes "Not Reported, or Unknown" injuries, so C here is wider than CCRS's C.
