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

## Status: LOCKED 2026-10-16 (Hermes session). Earlier "not locked" notes below are history.
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
- **Q9c DECIDED (by Hermes, user deferred: "pull, match, map back is fine"):** coverage is *reported*, not a pass/fail gate.
  The hidden-GPS test prints accuracy + coverage per tier; the dashboard shows placed/review/unmatched counts.
- **Q10 DECIDED (default, user didn't object):** review queue grouped by street pair (one decision places all its crashes),
  top guesses shown on the map, "can't place" option, fixes saved only with approval, report flags a data limitation
  if >10% of the study's crashes stay unplaced.
- **Q11 RESOLVED by inspection:** Jev access exists: `TYPESAFE_API_KEY` in `~/.typesafe/credentials`; client shim at
  `~/z0intelligence/shims/jevkit` (noul / choice / score; several questions per call; ~$0.042 per M input tokens).
- **Product priority (user, 2026-10-16):** CrashIQ is the *first deployable product*, ahead of DemandIQ, because the data
  is public and already sitting there (CCRS); the value is all in the analysis. Implication: Stage 7 (ship) is NOT
  deferred; v1 scope stays lean (profile/TIS mode) so it ships fast. Audience for the deployed version: to confirm.
- **R2.5 DECIDED:** v1 = corridor with study limits (start/end); every intersection along it is included (auto-detected,
  user edits the list). Intersection-only mode (no corridor) is NOT in v1; it comes with v2 ISOAP/SPICE.
- **Deployment DECIDED:** same path as DemandIQ: build and run locally, push to hosting when done. It will be a **paid
  product**. v1 local can keep the single `APP_PASSWORD`; before charging money it needs real user accounts, payments,
  per-user usage limits on Claude/Jev spend, and terms of use. Data licence checked: CCRS on data.ca.gov is
  "Other (Public Domain)" (CHP), so commercial use is allowed. To confirm before launch: no other licence issues
  (OSM data is ODbL: attribution required).
- **Runtime agent (proposed, awaiting "ok"):** Claude API tool-use loop (DemandIQ pattern) behind the swappable agent contract.
  Token plan, from ai-agent-validation #2 (model routing) and #9 (cost & latency); full check in Stage 3:
  (1) Claude never sees raw crash rows, only the computed summary tables + cross-tabs that flag something;
  (2) Jev does the high-volume cheap steps (J1 geocoding; J3 screening locations against the pattern library, so Claude
  writes up only the matches); (3) a small model or Jev routes simple follow-up questions straight to query tools;
  Sonnet only writes the findings; (4) prompt caching on the fixed parts (pattern library, instructions, examples);
  (5) hard spend cap per study, enforced in code; (6) tokens + $ logged per study. Target to verify in build:
  < $1 of AI per study (estimate ~$0.20–0.50 for Sonnet; measure, don't trust the estimate).
- **Model choice → decided by a bake-off, not upfront (user: cheap may be too weak, expensive too costly):** no skill in
  Hermes or ~/.claude covers model selection (searched). Method (tool-testing + ai-agent-validation #2/#6/#9): build the
  agent behind the swappable contract → golden set of ~10–20 corridors with the user-approved expected findings (seeded
  from the user's past analyses) → run Haiku / Sonnet / Opus tiers on the same inputs → score: findings correct vs golden,
  citation-validator pass rate, missed patterns, $ and seconds per study → pick the **cheapest tier that passes**, per
  step (routing/chat can be a smaller tier than findings). Re-run when a new model ships. Hosting: plain Anthropic API
  (no Bedrock needed).
- **Runtime agent DECIDED:** Claude API tool-use loop; model tier chosen by the bake-off. Nothing open.

## Session 2026-10-18 — research recommendations (issue #3), user answers
- **D1 YES, mode-driven:** outputs depend on the study mode chosen in Setup. Each mode declares the deliverables its
  agency requires; e.g. HSIP application mode → collision list + collision diagram per location appear in results
  and export. Modes that don't require them don't show them.
- **D2 YES:** HSM beta-binomial over-representation test (threshold proportion; ≥2 target crashes; similar-site
  reference group). NOTE for later: review whether a better over-representation method exists.
- **D3 YES:** Caltrans rate-group averages for State Highway System locations only; peer-group comparison elsewhere,
  labelled as such (never "statewide average" on local streets). Rates computed only where the mode needs them.
- **D4 YES (very important to user):** HSIP five severity levels; **one count per crash** (not per vehicle/party/victim);
  verify against CCRS fields (incl. whether PDO crashes are present). Open a **technical-nuances list**
  (docs/06-nuances.md): every doubt goes there, the user answers from 8 years of crash-analysis experience or we research.
- **D5 YES (2026-10-18):** pattern library seeded from HSM Ch. 6 (pattern → possible factors) and Caltrans LRSM App. B
  (crash type → accepted countermeasures); FHWA PSC only as a tag; every finding says "possible cause, verify in field".
- **D6 pending:** user likes the traceability but worries it's too much info for the end user. Proposal: collapsed by
  default (one small "Sources" link per finding); full audit detail in the PDF appendix for reviewers.
- **D7 YES (2026-10-18):** bake-off also scores agreement with the user's findings (kappa); internal only.
- **D8 LATER:** build the base product first; then review competitors (Citian etc.) and add features. Trademark later.
- **D9 YES (2026-10-18), matching method to confirm:** user uses the CMF Clearinghouse for ISOAP ("a whole digging game").
  Matching proposal: (1) code knows each location's over-represented crash types (D2), location type and conditions;
  (2) a curated, versioned countermeasure table, each row tagged with crash types addressed, location type, conditions,
  CRF/CMF, star rating, source ID (LRSM row or Clearinghouse CMF ID); built once, refreshed periodically, not scraped
  per study; (3) code filters by tag match, ranks by expected crashes reduced on that location's own target crashes,
  then star rating; (4) user picks; combination rules enforced (Caltrans max 3; warn when multiplying >2 CMFs).
  Proposal to confirm: HSIP mode uses Caltrans' own LRSM countermeasure table (closed list, required by HSIP);
  Clearinghouse used in ISOAP/general modes as a curated shortlist (star rating, crash types), not a full ingest.
- **D10 YES:** ISOAP mode as a Stage 1 package (SPICE + conflict-point / Safe System score + observed history).
- **Phasing DECIDED in principle:** one complete process at a time, not many in parallel. Proposed order (to confirm):
  P1 core crash profile (foundation) → P2 HSIP application → P3 ISOAP → P4 traffic-study safety section, ATP, LRSP/HIN.
- **Market DECIDED (2026-10-18):** goal is to grow across US states, one state at a time. **California first** (user is
  there and can reach clients), then the next state. Design implication: everything state-specific sits behind a
  **state pack** (crash data source + field mapping, severity mapping, rate tables, countermeasure/CRF list, crash costs,
  study-mode formats such as HSIP/ISOAP). The core (map, assignment, profile, tests, findings, audit, export engine)
  stays state-neutral. Adding a state = adding a pack, not rewriting the app. Cheap to do now; expensive to retrofit.
  User confirmed: build the pack structure, but **only the California pack is active**. Next state likely **Texas**;
  Hermes does the background research for it (data source, severity, HSIP-equivalent formats) when the user says go.

## Pipeline status
`[new-tool] Stage 2 done (LOCKED 2026-10-16) → Stage 3: design check.`
Resume: confirm R2.5 (intersection-only mode), settle runtime/build agent, then Stage 3 design check.
