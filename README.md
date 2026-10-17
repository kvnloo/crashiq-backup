# CrashIQ

Crash safety analysis for California corridors. Draw a corridor with study limits, and CrashIQ pulls every
reported crash from CHP's CCRS open data (data.ca.gov). It places crashes that have no coordinates, builds a
deterministic crash profile, and has an AI analyst write findings, with every number traced to a computed table.
Export to Excel and PDF.

Part of the Traffic Engineer Oracle (shares the project context object with DemandIQ).

## Status
Pipeline stage 3 (design) is done. Next is stage 4 (build).

## Docs
- `docs/01-kickoff.md`: job statement, phasing (v1 profile → v2 SPICE/ISOAP → v3 CMF countermeasures)
- `docs/02-spike-ccrs.md`: CCRS data spike (coverage, coordinate gaps)
- `docs/03-requirements.md`: locked requirements
- `docs/04-design.md`: components, AI vs code split, spine fields, validation scorecard

## Principles
- Code computes every number. AI only interprets and writes, and an unsourced number is rejected.
- Every crash location and every finding carries provenance.
- Nothing is learned without user approval.

## Stack (planned)
FastAPI + Vite/React + Leaflet (DemandIQ shell), SQLite, Claude API, Jev (TypeSafe) for typed matching.

## Data
CCRS crash data: California Highway Patrol, public domain. Map data © OpenStreetMap contributors (ODbL).
