# Tennessee methods (Hermes, 2026-11-08)

Manual downloaded to `~/.hermes/state-manuals/tn/`:
- TDOT, *Highway System Access Manual, Volume 2: Intersection & Interchange Evaluation* (2021-01-29), sha256 e927db03…72994e,
  <https://www.tn.gov/content/dam/tn/tdot/traffic-engineering/hsam/TDOT%20HSAM%20Vol%202%20IIE%20012921.pdf>.
- FHWA's Tennessee HSIP 2024 report could not be downloaded (bot wall); not used.

| value | Tennessee | where |
|---|---|---|
| crash costs | **missing**: HSAM sends users to the LCCET tool, option "Fatality, injury, PDO"; no dollar table | HSAM Vol. 2 p. 2-74 (PDF p. 82) |
| statewide average rates | from TDOT's STID on request; none published | HSAM Vol. 2 p. 2-19 (PDF p. 27) |
| critical rate | compared at a **99 percent** confidence level | HSAM Vol. 2 p. 2-19 (PDF p. 27) |
| years | "most recent three-year period of crashes" (intersection evaluation) | HSAM Vol. 2 p. 2-18 (PDF p. 26) |

CrashIQ screens with the HSM critical rate against the corridor's own sites (national method, user decision, K = 1.645),
noted in `screening.state_method`; TDOT's 99% level is recorded, not applied.
