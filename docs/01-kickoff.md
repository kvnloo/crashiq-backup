# CrashIQ — Kickoff decision (2026-10-15)

## Job statement (Stage 1 gate)
CrashIQ is for traffic engineers doing safety studies in California. The user
draws a corridor on a map. The tool pulls every reported crash in that corridor
from CHP's CCRS open data, then builds a deterministic crash profile: counts,
KSI, severity mix, collision types and temporal patterns. It runs a SPICE-style
evaluation of control types at the intersections in the corridor and matches the
crash patterns found to CMF Clearinghouse countermeasures. An AI agent reads
these computed results and writes the findings and a draft report. The agent
never computes numbers itself. Output: a web dashboard, exportable to Excel and
PDF. CrashIQ is a separate repo and an Oracle tile, sharing the project context
object with DemandIQ.

## Decisions
- **Stack:** same as DemandIQ (FastAPI + Vite/React + Leaflet). Separate repo.
- **Data:** CCRS auto-pull from data.ca.gov (spike first). Fallback: TIMS CSV upload.
- **SPICE:** public FHWA/Caltrans tool. We reimplement its method in Python and
  golden-test it against the Excel tool.
- **CMF:** public FHWA CMF Clearinghouse.
- **AI rule:** code computes every number; the agent only interprets and writes.
- **Output:** web dashboard → Excel + PDF export.

## Phasing
1. v1: corridor → CCRS crashes → crash profile → AI findings → export
2. v2: SPICE intersection control evaluation (AADT from DemandIQ / manual / Traffic Census)
3. v3: CMF countermeasure matching + B/C screening

## Not building
Live TIMS scraping, our own SPF calibration, collision-diagram drawing (later).

## Riskiest assumption
CCRS on data.ca.gov has usable lat/long and enough history (3–5 years) to
support a corridor safety analysis. → Spike before Stage 2 is finalized.
