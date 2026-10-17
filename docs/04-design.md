# CrashIQ — Stage 3 design note (2026-10-16)

Inputs: `01-kickoff.md`, `02-spike-ccrs.md`, `03-requirements.md` (LOCKED). Skills applied:
ai-agent-validation (design-time pass, mixed-system rules), oracle-spine (context object + data registry).
Scope: **v1 only** = corridor with study limits → CCRS crashes → crash profile → AI findings → Excel/PDF.
v2 (SPICE/ISOAP, intersection-only mode) and v3 (CMF countermeasures, B/C) are out of this note.

## 1. Components

| # | Component | Kind | What it does |
|---|---|---|---|
| C1 | `study` | code | Project, mode, year window (default last 5 complete years; 1–10), study limits |
| C2 | `network` | code | Polyline → OSM (Overpass) snap → intersections + segments; user edits list. Reuse DemandIQ corridor code |
| C3 | `ccrs` | code | Resolve per-year resource IDs at runtime; pull Crashes/Parties/InjuredWitnessPassengers via CKAN SQL (bbox + buffer, plus no-coordinate rows in the city/county whose street names match); cache per project |
| C4 | `locate` | code + **Jev** | Place every crash: GPS → exact name match → fuzzy → Jev Choice (leftovers only) → review queue. Tag `gps/exact/fuzzy/jev(p)/user/unmatched` |
| C5 | `assign` | code | HSM rule: ≤250 ft → intersection crash; on corridor → segment crash; outside buffer → excluded (counted) |
| C6 | `profile` | code | Counts, KSI (KABCO from IWP), severity mix, collision type, PCF, temporal heatmap, party/mode, per-location tables, crashes/mi/yr; rates only when AADT entered |
| C7 | `crosstab` | code | Per-location attribute cross-tabs + over-representation tests vs a baseline (corridor / city / county) → list of *signals* |
| C8 | `patterns` | data + **Jev** | Pattern library (HSM Part B, Caltrans LRSM, FHWA PSC): symptom → factors → countermeasures. Jev Noul screens each signal × library entry (J3); only matches go to Claude |
| C9 | `analyst` | **Claude** | Reads matched signals + tables + library entries + approved examples → findings JSON with citations. Never computes numbers |
| C10 | `validator` | code (+ Jev J2 later) | Rejects any finding whose numbers don't appear in a cited table, or whose evidence can't be produced |
| C11 | `review` | UI | Findings ✓/✗/edit, evidence drill-in (records + map + cross-tab), follow-up chat via query tools; geocode review queue grouped by street pair |
| C12 | `memory` | code | Accepted findings → worked examples (with data signature + provenance); library additions only with approval |
| C13 | `export` | code | Excel + PDF per mode (v1: profile/TIS) |
| C14 | `spine` | code | Read/write the Oracle project context object |
| C15 | `budget` | code | Per-study $ cap on Claude + Jev, token/$ log per study |

Stack: FastAPI + Vite/React + Leaflet, DemandIQ shell (TopBar, Sidebar, MapView, themes, step flow).
Storage: SQLite locally (projects, crash cache, geocode decision cache, findings, examples, library).

## 2. AI vs deterministic split

- **Deterministic (code):** C1–C3, C5–C7, C10, C12–C15, plus every number in the product.
- **Jev (typed, probabilistic):** J1 geocode leftovers (Choice), J3 signal screening (Noul). J4 chat routing later.
- **Claude:** C9 narrative findings + follow-up chat answers, only from tool outputs.
- **Seams (where AI output meets math), each with a code contract:**
  1. Jev J1 → coordinates: pick must be from the code-generated list; p ≥ τ and margin ≥ m (τ, m from the
     hidden-GPS test: ≥98% correct on 1,000 same-city crashes). Else → review queue. Coordinates always computed by code.
  2. Jev J3 → analyst input: a missed screen only means Claude never sees that signal. Guard: high-severity signals
     (KSI clusters) bypass the screen and always go to Claude.
  3. Claude → findings: validator checks every number against its cited table; unsourced → rejected, not shown.

## 3. Oracle spine — fields in / out

**Reads:** `project.*`, `corridor.termini`, `corridor.geometry_ref`, `corridor.intersections[]` (name, control, legs),
`corridor.functional_class`, `context.setting`, AADT if a DemandIQ object supplies it (later).
**Writes:** `corridor.intersections[]` (if absent, auto from OSM, method `auto`), `analysis.flags[]`
(`type: safety_pattern | data_gap`, e.g. "38% of crashes unplaced in SF" → `data_gap`), `analysis.completed += "crashiq_profile"`,
`data_holdings += {kind: "CCRS", period, path_or_ref}`, and a new **`safety`** block. Provenance on every field
(source CCRS/OSM, method auto/manual/ai, date, confidence for ai).

**Spine extension needed (rule 4: extend in the spine, not privately):**
```json
"safety": {
  "window": {"from_year": null, "to_year": null, "preliminary_included": false},
  "locate_summary": {"gps": 0, "exact": 0, "fuzzy": 0, "jev": 0, "user": 0, "unmatched": 0},
  "locations": [ {"id": "", "kind": "intersection|segment", "crashes": 0, "ksi": 0,
                  "crashes_per_mi_yr": null, "rate": null} ],
  "findings": [ {"id": "", "location_id": "", "pattern_ref": "", "evidence_refs": [], "status": "accepted"} ]
}
```

**Data sources:** CCRS on data.ca.gov (public domain, CHP; replaces SWITRS/TIMS in the registry; registry entry to
update), OSM/Overpass (ODbL, attribution), Caltrans Traffic Census (later, SHS AADT).

## 4. ai-agent-validation — design-time scorecard

| # | Item | Mark | Decision |
|---|---|---|---|
| 0 | Demo vs production | ✅ | Real side effects are limited to writing findings/memory; no external actions |
| 1 | Topology | ✅ | Single analyst + deterministic pipeline; not an autonomous multi-agent system |
| 2 | Model routing | ✅ | Jev for volume; small tier for chat routing; findings tier by bake-off (cheapest that passes) |
| 3 | Tool contracts | ⚠️ | Write typed contracts + "cannot do" per query tool in Stage 4 (contract first) |
| 4 | Memory vs state | ✅ | Run state in SQLite (a crashed study resumes from cached pulls/decisions); examples = episodic; library = semantic |
| 5 | Loop | ✅ | Analyst loop: step cap (e.g. 12 tool calls), goal = findings JSON validates, trace ID per step |
| 6 | Trace evals | ⚠️ | Bake-off golden set (10–20 corridors) + hidden-GPS test; needs user's past analyses → see flag F1 |
| 7 | Approval gates | ✅ | User approves findings before export and before anything is learned |
| 8 | Fallbacks | ✅ | CCRS slow → per-county snapshot; Jev down → review queue; Claude down → profile + tables export without narrative |
| 9 | Cost & latency | ✅ | Target < $1 AI per study, logged; p95 study < 60 s after the CCRS pull is cached |
| 10 | Context design | ✅ | Claude sees signals + cited tables only, never raw rows; fixed parts prompt-cached |
| 11 | Observability/privacy | ✅ | Trace per study; keys server-side only; CCRS is public data |
| 12 | Injection | ✅ | Untrusted text = CCRS free-text fields + chat. Analyst tools are read-only; free text passed as data, not instructions |
| 13 | Sandboxing | N/A | Agent runs no code |
| 14 | Harness tests | ⚠️ | Stage 5: seam rejection tests (unsourced number, out-of-list Jev pick, injected text in a CCRS field) |
| 15 | Budget cap | ✅ | Per-study $ cap enforced in code (C15) |
| 16 | Memory provenance | ✅ | Every example/library entry records who approved it, when, from which study |

**Critical gaps:** none on paper. **Major:** #3 and #14 are Stage 4/5 work by design. **Open flag F1** below.

## 5. Open flags
- **F1 (user):** golden set = the user's past crash analyses. The oracle-spine boundary says the platform uses public
  data only and employer work products stay outside. If the past analyses are employer deliverables, use them only
  as private local test fixtures (never in the shipped product or its memory), or rebuild equivalent cases from public
  CCRS data. Needs the user's call.
- **F2:** LA City 2024 count looked low in the spike. Check against TIMS for one known corridor in Stage 4.

## Gate
Components, AI/deterministic split, spine fields in/out, data sources: written. → Stage 4 (build), after F1.
