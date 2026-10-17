# CrashIQ — Requirements (grill-me, in progress)

Decisions are recorded as they're made. Each one cites its question.

## R1 — Study types (Q1)
One analysis engine, several **study modes**. Each mode decides which analyses
run and what the export contains:

| Mode | Basis | Core content |
|---|---|---|
| Crash profile / corridor screening | Historical | Counts, KSI, severity, collision types, temporal, hot spots |
| Traffic-study safety section (TIS/TIA, LRSP) | Historical | Profile + rates vs statewide averages + findings |
| HSIP application | Historical + B/C | Crash history in the HSIP window, CMF-based B/C (Caltrans HSIP calculator method) |
| ISOAP / ICE (Steps 1–2) | **Predictive** | SPICE predicted crashes by control type, ranked alternatives |
| ATP grant | Historical (general) | Safety need narrative, ped/bike focus, crash history |

- Every mode exports to Excel + PDF in the format that study type expects.
- Requirements per mode get pinned down from Caltrans guidance
  (caltrans-traffic-expert skill) during design, not guessed.
- The user will supply examples of their past analyses later. Treat them as
  golden references for format and content.
- Build order still follows the phasing: the profile/TIS mode first, because
  every other mode reuses it.

## R2 — Study area & crash assignment (Q2)
1. User draws a polyline. It snaps to the OSM network and intersections are auto-detected (DemandIQ pattern).
2. User reviews the list: add, remove or rename intersections, and flag the study intersections.
3. Crashes are assigned by the HSM convention: within the 250 ft influence area → intersection crash;
   otherwise on the corridor → segment crash (between adjacent study intersections);
   outside the buffer → excluded, with the count shown.
4. Influence radius (default 250 ft) and corridor buffer are user-adjustable.
5. **Also supported: intersection-only mode.** The user picks one or more intersections with no corridor
   (typical for ISOAP/ICE). Segment analysis is skipped. *(Interpretation of the user's reply. Confirm.)*

## R3 — Volumes / exposure (Q3)
- v1: **manual entry only**, and only when the user turns on crash rates (or a mode needs them).
  - Segments: AADT per segment.
  - Intersections: major and minor approach AADT (entering vehicles).
- Without volumes: counts + crashes/mile/year only, and the report says rates weren't computed.
- Later: DemandIQ context-object import, Caltrans Traffic Census auto-fill for the SHS, statewide-average comparison.

## R4 — Agent role: pattern diagnosis (Q4)
- **Python does the data work.** It assembles, cleans and tabulates everything,
  including attribute cross-tabs per location (lighting × time × collision type ×
  movement × severity, …) and overrepresentation tests against a baseline.
- **The agent's core job is finding patterns.** Examples:
  - "nighttime crashes on segment 3, dark–no street lights" → lighting is a likely factor
  - "Intersection B: KSI concentrated in right-turn / broadside crashes" → turning conflict / sight distance
- The agent is grounded in a **crash pattern library**: symptom → possible contributing factors →
  candidate countermeasures, built from published guidance (HSM Part B diagnosis and
  countermeasure tables, Caltrans LRSM, FHWA Proven Safety Countermeasures). Every finding cites
  the library entry and the computed table it rests on.
- Numbers the agent writes are checked against the computed tables; a number with no source is rejected.
- **Follow-up chat**: yes. Answered through the same deterministic query tools.
- The user edits and approves findings before export.
- "Gets better over time": see Q5.

## R5 — Learning loop (Q5)
- Each finding has ✓ accept / ✗ reject / edit.
- **Every finding shows its evidence.** One click opens the actual crash records behind it
  (filtered list + map highlight + the cross-tab). The user verifies against the data before accepting.
  A finding whose evidence can't be produced isn't shown.
- Accepted findings + their data signature become **worked examples**; the agent retrieves similar
  past cases on later analyses.
- **Pattern library**: guideline-seeded (HSM Part B, LRSM, FHWA PSC). User-written findings that
  the library lacks are proposed as new entries and added only with approval.
- The user's past analyses (to be supplied) seed the examples and the test cases.
- No silent changes: everything the agent learns is user-approved and traceable.

## R6 — Data window & scope (Q6)
- Default **5 most recent complete years**; selectable **1–10 years** (CCRS starts 2016).
- Modes can enforce their own windows (e.g. HSIP cycle rules), with a warning if overridden.
- `Is Preliminary` records are included but flagged; listed in the report caveats.
- Window includes 2020 → COVID-anomaly note.
- Pull all three CCRS tables: Crashes, Parties (movements, modes, at-fault, age), InjuredWitnessPassengers (KABCO for KSI).

## R7 — Screen flow (Q7)
1. Setup (mode, project name, year window)
2. Study area (draw corridor / pick intersections)
3. Review locations (intersections, segments, 250 ft + buffer, AADT if rates on; crashes colored by location confidence)
4. Crash profile dashboard (KPIs, severity map, collision types, PCFs, temporal heatmap, top locations; per-location drill-in)
   - v2: ISOAP prediction step (SPICE) after 4
5. Findings (agent diagnoses + evidence + ✓/✗/edit + follow-up chat)
   - v3: Countermeasures step after 5
6. Export (Excel + PDF, mode-specific format)

## R8 — Deployment & platform (Q8)
- Same as DemandIQ: local dev first → Render, single Docker service, `APP_PASSWORD` basic auth, `ANTHROPIC_API_KEY`.
- LLM: Claude API, current Sonnet for the agent.
- Crash data: live CCRS pull from data.ca.gov per study, cached per project. Fallback if too slow: per-county snapshot.
- Persistence (new vs DemandIQ): projects, accepted findings/worked examples, pattern library →
  SQLite locally; persistent disk or Postgres when hosted.
- Users: the user + a small number of colleagues / demo viewers.

## Status: NOT locked (2026-10-16)
The full picture is agreed in direction. The user is exploring Hermes Agent and "Software Factory" next.

### OPEN — two agent decisions (kept separate)
1. **Runtime agent**: the analyst inside CrashIQ that diagnoses patterns. Candidates: plain Claude API
   tool-use loop (DemandIQ pattern), Claude Agent SDK, Hermes Agent (Nous Research).
2. **Build agent**: how CrashIQ gets built. Candidates: Claude Code + new-tool pipeline (current),
   a Software Factory approach (agents build from spec + tests).

Hold regardless of choice: the **agent contract** (inputs = computed tables + pattern library + approved examples;
tools = deterministic query functions; output = findings JSON with citations; validator rejects
unsourced numbers; user approval before anything is learned). The runtime must be swappable behind it.

### PROPOSED — Jev (TypeSafe System One) placement (2026-10-16, not locked)
Three layers: **Python** = all math and data (deterministic) · **Jev** = fast typed judgments
(Choice / Noul / Score + probabilities) on high-volume semantic steps · **Claude** = narrative + reasoning.
Note: Jev is typed and calibrated, but *not* deterministic. Validate it on labeled cases (tool-testing mixed-system rule).

| # | Where | Jev primitive | Why it's a fit |
|---|---|---|---|
| J1 | Geocode crashes with no coordinates: pick which corridor intersection "CRENSHAW BLVD / I-105 W/B" means | Choice over code-generated candidates + "no match" | Biggest data gap (SF/Sac ~65% missing coords); select-not-generate; thousands of rows |
| J2 | Verify every Claude finding against its cited evidence | Noul ("does this table support this claim?") | Universal-verification pattern; stronger than number-matching alone |
| J3 | Screen locations against pattern-library symptoms | Noul per library entry | Cheap fan-out; Claude only writes up the matches |
| J4 | Route follow-up chat to a query tool + params | Choice (function-calling pattern) | Simple questions skip Claude entirely |
| J5 | Normalize free-text "Other" fields (collision type, object struck) | Choice | Recovers data that would otherwise be dropped |
| J6 (v3) | Rank CMF candidates / similar worked examples | Score / rerank | Retrieval for countermeasures + learning loop |
Low-confidence Jev answers → shown as "needs review", never silently accepted.

### J1 detail — geocoding crashes with no coordinates (revised 2026-10-16 via ai-agent-validation mixed-system rules)
**Line between code and Jev.** Code does everything except one step: picking which candidate a messy
street pair means.
1. Code: build candidate intersections from OSM for the corridor's city (cross-street pairs + aliases).
2. Code: normalize names (suffixes, directionals, route aliases like SR-1 = 19th Ave, ramp tags like "W/B").
   Alias table is a versioned file, not a prompt.
3. Code: exact match, then fuzzy match. A match is accepted only if both streets match and it's unambiguous.
4. Jev Choice, **leftovers only**: top-5 code-generated candidates + "none of these". Jev picks; it never invents a location.
5. Seam check (code): the pick must be in the list, top probability ≥ τ, and margin over 2nd ≥ m. Otherwise → review queue.
6. Code: offset SecondaryDistance/Direction along PrimaryRoad → coordinates → normal 250 ft assignment.
**Provenance on every crash:** `gps` / `exact` / `fuzzy` / `jev(p)` / `user` / `unmatched`. Dashboard shows counts per tier.
Every analysis can be re-run excluding `jev` crashes.
**Cache:** decisions keyed by (city, normalized primary, normalized secondary). One decision covers every crash
with that string pair, which keeps calls few and results repeatable.
**Fallback:** if Jev is down or over budget, leftovers go to the review queue. Analysis never blocks.
**Learning:** user review corrections → proposed alias-table entries (added only with approval) + new test cases.
**Calibration with no hand-labeling:** crashes that HAVE coordinates also have street names. Hide the coords, run the
pipeline, score against truth (correct = assigned to the same study location / within 250 ft). Use same-city rows,
because a geocoding gap is agency-dependent. τ and m come from this test, not a guess. Arms: code-only, +fuzzy, +Jev, +Claude.
Jev ships only if it beats fuzzy on accuracy at equal review rate.
Status: PROPOSED, needs user confirmation (see Q9–Q11 below).

## Session 2026-10-16 (Hermes, resumed)
- **Build agent DECIDED:** Hermes runs the new-tool pipeline using the Claude skills (user: Hermes keeps going without losing info).
- **Jev DECIDED in principle:** J1 (crashes with no coordinates) is Jev's primary job. J2–J6 stay proposed.
- **Layout DECIDED:** reuse the DemandIQ frontend shell (TopBar, Sidebar, MapView, themes, step flow); swap in the CrashIQ screens.
- **Q9 DECIDED:** auto-place bar = **98% real accuracy** (user: "1000 crashes, 980 accurate"). Measured on the hidden-GPS
  test, 1,000 same-city crashes (user confirmed 1,000, not 100,000); correct = same study location / within 250 ft of true GPS. The Jev cut-off τ is set
  where crashes above it are ≥98% right; below → review queue. Note: at n=1,000 a measured 98.0% has ~±0.9% noise,
  so pick τ where the measured value is clearly above 98% (lower confidence bound), or test on more crashes.
- **Q9b — what if it doesn't pass (user asked):** Jev isn't trained by us; it's a fixed model. The 98% bar is enforced by
  the cut-off, so accuracy always holds; what a weak matcher costs is *coverage* (more crashes sent to review).
  Pass/fail therefore needs two numbers: accuracy ≥98% AND coverage ≥ X% (coverage target: Q9c, pending).
  If it fails, levers in order: (1) improve the code side: alias table, candidate list, name cleaning (biggest, cheapest);
  (2) give Jev better state (nearby streets, distance/direction, city); (3) try Claude on the leftovers instead;
  (4) no AI: code matches + review queue. The tool still works without Jev; it's an optional booster.
- Open: Q10 review queue size · Q11 Jev access · R2.5 · runtime agent.

## Pipeline status
`[new-tool] Stage 2: resumed 2026-10-16 in Hermes (grill-me). Requirements not locked yet.`
Resume: confirm R2.5 (intersection-only mode), settle runtime/build agent, then Stage 3 design check.
