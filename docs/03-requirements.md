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
**5 steps** (user decision 2026-10-18, issues #5/#6/#8; was 6 — Study area and Review locations merged into one Corridor step):
1. Setup (mode, project name, year window). Keeps the traffic animation, headline above it, never on top of it.
2. Corridor: draw corridor / pick intersections, then review locations on the same screen (intersections, segments, 250 ft + buffer, AADT if rates on; crashes colored by location confidence)
3. Crash profile dashboard (KPIs, severity map, collision types, PCFs, temporal heatmap, top locations; per-location drill-in)
   - v2: ISOAP prediction step (SPICE) after 3
4. Findings (agent diagnoses + evidence + ✓/✗/edit + follow-up chat)
   - v3: Countermeasures step after 4
5. Export (Excel + PDF, mode-specific format)

## R8 — Deployment & platform (Q8)
- Same as DemandIQ: local dev first → Render, single Docker service, `APP_PASSWORD` basic auth, `ANTHROPIC_API_KEY`.
- LLM: Claude API, current Sonnet for the agent.
- Crash data: live CCRS pull from data.ca.gov per study, cached per project. Fallback if too slow: per-county snapshot.
- Persistence (new vs DemandIQ): projects, accepted findings/worked examples, pattern library →
  SQLite for v1, locally and when hosted (persistent disk). **PostgreSQL not needed for v1** (user, 2026-10-18).
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
**Provenance on every crash:** `gps` / `address` / `exact` / `relaxed` / `near` / `fuzzy` / `jev(p)` / `user` / `review` / `unmatched` (address/relaxed/near/review added by the user 2026-10-18, PR #16). Dashboard shows counts per tier.
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
- **D6 YES, collapsed (2026-10-18):** audit block hidden by default: one small "Sources" link per finding; full audit
  detail in the PDF appendix for reviewers (user: avoid too much info for the end user).
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
- **Phasing DECIDED (2026-10-18):** one complete process at a time, not many in parallel. Order confirmed:
  P1 core crash profile (foundation) → P2 HSIP application → P3 ISOAP → P4 traffic-study safety section, ATP, LRSP/HIN.
- **Market DECIDED (2026-10-18):** goal is to grow across US states, one state at a time. **California first** (user is
  there and can reach clients), then the next state. Design implication: everything state-specific sits behind a
  **state pack** (crash data source + field mapping, severity mapping, rate tables, countermeasure/CRF list, crash costs,
  study-mode formats such as HSIP/ISOAP). The core (map, assignment, profile, tests, findings, audit, export engine)
  stays state-neutral. Adding a state = adding a pack, not rewriting the app. Cheap to do now; expensive to retrofit.
  User confirmed: build the pack structure, but **only the California pack is active**. Next state likely **Texas**;
  Hermes does the background research for it (data source, severity, HSIP-equivalent formats) when the user says go.

- **Geocoding decisions (user, 2026-10-18, PR #16):**
  (1) Test design = the original one: hide the record's own GPS and place it from the report (Long Beach run). Other sources
  (DataSF etc.) are not the test truth; sources disagree. Result so far: Jev loses to code matching (LB clean GPS 92.6% vs 95.2%;
  SF 88.1% vs 92.5%), so Jev is a review suggestion only, never an auto-placer.
  (2) Placement gate: decide later. Unplaced crashes go to the review list; why they don't place is backlog #17.
  (3) Address tier: keep (best location from whatever the record gives, as the user did by hand).
  (4) Provenance labels `address`, `relaxed`, `near` added (see above).
  (5) City crash maps (DataSF etc.): verification/tallying only, not a placement source.
  (6) Anthropic API key: user will set one up, **deferred to the end** of the build (user, 2026-10-18).
  (7) LA truth source: **dropped** (user, 2026-10-18). No LA truth test; LA counts are covered by the #18 source check.
- **Tool and stack decisions (user, 2026-10-18, after #20):**
  (1) **libpostal dropped.** It would add about $60/month of hosting (4 GB instance, #20) for no gain: in Claude Code's
  bake-off (commit 1509d39, `knowledge/tools.md`) it was slightly more accurate but placed fewer crashes than our locator.
  The "libpostal as fallback" idea in that file is dropped with it.
  (2) **Anthropic API key deferred to the end.** Build and test everything that doesn't need Claude first; the key is set up last.
  (3) **LA truth question dropped** (geocoding decision 7 above).
  (4) **PostgreSQL not needed: SQLite for v1** (R8). So the PostGIS TIGER geocoder is out for v1; if TIGER is used, it is loaded
  into our own locator (#20 Q1 option B).
- **New requirement (user, 2026-10-18):** before analysis, a **state-level validity check of crash data sources**: best source per
  state and road type (CA: TIMS for city streets, CHP/CCRS for freeways), cross-check where several exist, reach consensus,
  then analyse. Research: issue #18.

## Pipeline status
`[new-tool] Stage 2 done (LOCKED 2026-10-16) → Stage 3: design check.`
Resume: confirm R2.5 (intersection-only mode), settle runtime/build agent, then Stage 3 design check.

- **Two maps DECIDED (user, 2026-10-18):** use both OSM and Census TIGER street networks for crash placement
  (practice data: +1–2 crashes placed per 100 at about the same accuracy; free). Scheduled as a later task under #17,
  not part of PR #16.
- **#49 DECIDED (user, 2026-10-18):** option 1, strict backup rule when locations look alike (fewer, stronger findings;
  every number still visible in the tables).
- **#34 Stage 4 defaults DECIDED (user, 2026-10-18, product-kickoff roundtable, relayed by Claude Code on #34):**
  (1) corridor buffer 100 ft (keep); (5) screen thresholds ≥5 crashes at the location, ≥3 of the type, P ≥ 0.80 (keep);
  (7) expected-rate comparison = both: critical rate vs similar sites on the corridor (HSM Ch. 4) + TASAS averages when the
  corridor is a state highway; (8) default window ends at the last finalized CHP year, engineer can override;
  (3/11) intersection volumes = two-way AADT for major and minor road; code computes entering volume = major + minor (4-leg),
  major + minor/2 (T); (9) freeway crashes excluded by default, include switch for ramp-terminal studies;
  (10) segment length center to center (HSM Part C Sec. C.6.2), stated in the report; (12) injury level unknown (U) kept as
  its own level; (13) COVID note for both 2020 and 2021; (14) dark split into with / without street lights;
  (15) warn when the window is under 3 years; (16) multiple-comparisons disclosure note.
  **Still open:** item 6 (user approves the pattern library; stays "draft" until then); items 2 and 4 (AI cap, Claude prices)
  parked with #55, AI analyst stays off, no API key.
  Roundtable build order ("first real corridor"): user runs live contract test on his Mac → build these decisions →
  critical rate + TASAS comparison → PCF categories + DUI/speed rows from an official code table → flag crashes whose GPS
  point is far from the stated road → one real corridor end to end (Stage 5 gate).
- **Hermes retired DECIDED (user, 2026-10-18):** Hermes can't run free (needs an API key or extra-usage credits), so
  all work moves to Claude Code on the Max plan: issues, docs, builds and reviews. Parallel work = separate Claude Code
  sessions (one issue/branch/worktree each, Remote Control allowed); a different session reviews each PR; decisions are
  asked in chat, not over WhatsApp. Rules: `CLAUDE.md`.
- **#39 DECIDED (user, 2026-10-18, in the PM session):** a corridor keeps only crashes on the corridor street and at the
  intersections it actually passes through. Crashes on side streets (cross street not one of the corridor's own
  intersections) are excluded. This is the user's standard practice. Like buffer exclusions (C5), excluded crashes are
  counted and listed with the rule, never dropped silently. The match is against the corridor's intersections, not any
  street that happens to be nearby on the map.
- **Grade separation (user, 2026-10-18, nuance N7):** a road that passes over or under the corridor (an interchange,
  overcrossing or undercrossing) is not an intersection of the corridor. Its crashes must not count for the corridor,
  and for a freeway corridor the crossing road's and interchange crashes must not count as freeway crashes. Detection
  rules: #67.
- **PM session merges DECIDED (user, 2026-10-19):** once a PR's review is clean and tests pass, the PM session merges it;
  the user isn't the merge step. Anything waiting on a user decision still waits. Rule: `CLAUDE.md`.
- **Tester session DECIDED (user, 2026-10-19):** a third standing session tests data and screens independently and never
  changes app code. Bugs are `bug` issues with a failing test → Engineering fixes → PM reviews and merges → Tester
  re-verifies. Own worktree, own database copy (`data/tester.sqlite`), ports 8001/3101. First tasks: (1) statewide CCRS
  profile of how each reporting agency records crashes (GPS rate, name style, offsets, blanks, PDO share, report
  versions, crashes piled on one point) to flag Union City–type cities; (2) TIMS comparison by county (the user signs
  in; no login bot, no passwords); (3) scripted screen tests (no AI steps, telemetry off).
- **GPS check distance DECIDED (user, 2026-10-19, PM session):** a GPS crash more than 400 ft (plus the reported
  offset) from the intersection its report names is flagged and counted where the GPS puts it, never moved (#53, PR #74;
  `assign.GPS_CHECK_FT`).
- **Injury levels (N3) DECIDED (user, 2026-10-19, PM session):** older SWITRS wording and the 2020+ KABCO wording are
  the same levels: Fatal = K; Severe injury = Suspected serious injury = A; Other visible injury = Suspected minor
  injury = B; Complaint of pain = Possible injury = C; no injury = O. Live CCRS codes (`SuspectSerious`, `*Inactive`,
  ...) map the same way (#75, PR #76). No report note about the 2020 wording change. Unknown level stays U (#34 item 12).
- **Obvious bugs and same basis DECIDED (user, 2026-10-19, PM session):** (1) obvious mistakes (the code doing other
  than what the docs say) are fixed and merged without waiting for the user; only choices go to the user. (2) Every
  check and comparison uses the same basis (data snapshot, years, corridor geometry and settings, the app's own code at
  a stated commit, the same crash and severity definitions). Rules: `CLAUDE.md`.
- **No cross street DECIDED (user, 2026-10-19, PM session):** a crash with no GPS whose report names the corridor but
  no cross street (`NOT STATED`, blank) goes to the review list for the engineer to place or exclude; it is not
  auto-excluded. `private_property` stays excluded. Build: #94.
- **#52 safety tables DECIDED (user, 2026-10-20, PM session):** (1) **PCF categories:** the 24 official SWITRS
  categories, with the Vehicle Code section → category crosswalk rebuilt from CHP's own output (TIMS SWITRS records
  carry both PCF_VIOLATION and PCF_VIOL_CATEGORY). Keep sections that map to one category in ≥ 99% of records; list
  the rest as unmapped. Only the mapping is used, never TIMS crash data in the product. Check TIMS terms before paid
  launch. (2) **Heavy truck:** a party vehicle with 3 or more axles, or a truck-tractor (with or without trailer).
- **Placement gate stays exact-only DECIDED (user, 2026-10-20, PM session; #116):** the 98% bar stands. "Same name
  except a leading direction" (COLORADO BL vs East Colorado Blvd) measured 82.5% (Wilson low 80.5%, n=1,574, Long Beach
  test half; 80.8% where East and West halves both exist), so it is not auto-placed; those crashes go to the review
  list, where "At suggestion" places a street pair in one click.
- **Heavy truck, trailers DECIDED (user, 2026-10-20, PM session):** a party whose vehicle is recorded as a trailer
  (semi-trailer, semi tank trailer, pull trailer, two trailers, etc.; a truck towing it) also counts as a heavy truck,
  since a tractor-trailer combination always has 3+ axles. Adds about 1,150 parties a year statewide (2024).
- **PCF 2024 extension DECIDED (user, 2026-10-20, PM session):** for every section key whose CHP category changed by
  year, use CHP's 2024 category for all years, so one violation counts the same way across a study. Applied (PR #137):
  most were "00 Unknown" in 2021–23 (e.g. 21954 → 10, 21955(a) → 10, 23103(a) → 17); 21809(A) was 09 and is now 17;
  22106(1) is 00 in 2024, so Unknown; 21760(A) has no 2024 records and stays visibly split (27 crashes statewide).
  Source: `data/reference/pcf_categories.md`.
- **Pedestrians and bicyclists first-class on tab 3 DECIDED (user, 2026-10-20, PM session):** vulnerable road users
  get their own prominent section (share of KSI, severity comparison, always-visible markers, ranking column,
  pedestrian context incl. day/night). Over-representation testing for them comes with Findings.
- **Testing methodology delegated to the PM session DECIDED (user, 2026-10-19, PM session):** in the user's words:
  "you're deep in the data, so you know better. I'll leave it for you to decide what's the right methodology."
  Scope: *how CrashIQ is tested* (test design, measures, matching method, run series, corridor lists for tests). It
  does **not** cover product methods, thresholds or rules that change what the app reports; those stay the user's.
  PM test-method calls so far: crash-by-crash ID matching with only computed fields re-checked (#88); like-for-like
  located % as the headline (#125); silent-drop check v3 beside v2 and a separately labelled corridor list v2 series
  (#148, #149). The user approved the run-history requirement and the same-basis rule (CLAUDE.md).
- **DMS-format GPS DECIDED (user, 2026-10-21, PM session; #143):** where an agency's CCRS GPS carries the
  degrees-minutes-seconds-written-as-decimal signature (San Jose PD: 85–88% of points 2021–24), convert it
  (37.142677 → 37°14′26.77″ → 37.2408). Per agency and year, only where the signature is clear. Keep a converted point
  only if it lands near the streets the report names (within the GPS-check distance of the named intersection or
  road); otherwise treat the crash as having no GPS. Provenance `gps_dms_corrected`, counted in the pull log.
  Evidence: 491 SJPD crashes linked to San Jose open data, median 34 km off as written, 80 m after conversion.
- **DMS-format GPS, partly affected years DECIDED (user, 2026-10-21, PM session; #143):** in agency-years where
  the DMS signature is elevated but not clear (50–75% of points; ordinary agencies run 30–40%), convert per crash:
  only if the point as written does not fit the report's streets and the converted point does. Every converted crash
  is labelled `gps_dms_corrected`. Clear years (≥ 75%) are converted as decided above. As for clear years, a DMS-signed
  point that fits neither way is treated as having no GPS.
- **Fatal crashes first (user direction, 2026-10-21, PM session):** fatal crashes get extra weight. Every fatal crash
  should be placed, even when the CCRS report has no GPS or cross street, using other sources: FARS (NHTSA, public
  domain) first, then a human-confirmed public-source lookup (e.g. news) for any remaining ones, always with the source
  cited and confirmed by the user (AI never sets a location). First step is measurement only (#166); building waits for
  the user's review of the numbers.
- **N9 e-bikes and e-scooters DECIDED (user, 2026-10-21, confirmed in the PM session):** e-bikes and e-scooters get
  their own road-user rows (own row in the road-user table, ranking column and map/strip marker), next to pedestrians,
  bicyclists and motorcyclists. Still open: whether motorized bicycles and ≤15 hp motor-driven cycles count with
  motorcycles.
- **N10 collision diagram direction (user, 2026-10-21, PM session):** use DemandIQ's *layout* conventions (the
  intersection cell, approaches by direction of travel, lanes laid out so arrows never overlap). The *symbols* follow
  standard collision-diagram practice, not DemandIQ's volume arrows: reference HSM Part B, Ch. 5 collision diagram
  (Figure 5-4) and agency legends (Seattle SDOT, NCDOT, Peel Region). The proposal is to be revised accordingly.
- **N10 collision diagram DECIDED (user, 2026-10-21, confirmed in the PM session):** DemandIQ layout (cell,
  approaches by direction of travel, no overlapping marks) with standard collision-diagram symbols (HSM Part B Ch. 5;
  NCDOT; Peel; Seattle) per docs/06 N10 revision 2. Property damage only = crossbar; night = filled arrowhead plus the
  HSM surface/light code; busy intersections = NCDOT stacking (identical crashes: same type, approach, at-fault party,
  road and light conditions share one symbol with a row of crash numbers); one diagram per study intersection, in the
  location drill-down and the PDF; each crash drawn on the at-fault party's approach. Build: #106.
- **Fatal crashes: FARS as a source DECIDED (user, 2026-10-21, PM session):** for a fatal crash with no usable location,
  use the linked FARS (NHTSA, public domain) point when it is street-consistent (same check as other GPS);
  provenance `fars`. Fatal crashes are listed first and red-flagged on the review list. For fatal crashes FARS can't
  place, the review list offers a lookup aid (prefilled public-source search by city, date, roads; no AI, no runtime
  API cost); the user places the crash and records the source link; provenance `user` with the source. Evidence: #166 /
  PR #172 (FARS street-consistent for 3,379 of 4,381 no-GPS fatal crashes, 2021–25).
- **FARS point must fit both named roads DECIDED (user, 2026-10-22, PM session):** when the CCRS report names two roads
  (corridor + cross street), a FARS point is used only if it fits both (within the GPS-check distance + offset of each);
  when the report names one road (no cross street), fitting that road is enough. Case: Palm Desert, FARS geocode 7.4 mi
  away on a long road (#191).
- **Parties fallback DECIDED (user, 2026-10-22, PM session):** when a CCRS Parties (or IWP) year isn't queryable in the
  data.ca.gov datastore but its file is downloadable (Parties_2025 since 2026-09-30), the server downloads the file once,
  keeps only the needed columns, caches it by resource and modified date, refreshes weekly, and serves study lookups
  from it; provenance noted in the pull log, and the #189 caveat clears for that year. The user also reports the load
  failure to data.ca.gov support.
- **"Unique pair" placement DECIDED in principle (user, 2026-10-22, PM session):** when a report's two streets can meet
  at only one place on the city network (e.g. `AVENUE J & 20TH ST W` → West Avenue J & 20th Street West; the user: "Avenue J
  will be intersecting with some other street... there's not going to be two"), place it there even if a name differs only
  by direction or suffix. It's built as its own tier (`unique_pair`), and it auto-places only if it meets the existing 98%
  bar (Wilson 95% lower bound) on the hidden-truth tests (#201); until then it goes to review with that suggestion.
- **GPS vs the report's own description DECIDED (user, 2026-10-22, PM session):** (1) **Snapped GPS:** when the police
  GPS sits at the named intersection but the report states a distance and direction from it ("200 ft north"), the
  report's description is right: place the crash at the named intersection plus the stated offset, along the named
  road (provenance `gps_offset_applied`). This refines the #53/#74 rule (GPS far from the stated intersection is still
  flagged and counted where it is). (2) **Default or dispatch-center points** (many crashes sharing one point, or a
  point far from the report's streets) aren't the crash location: treat them as no GPS and place by street names.
  (3) Wrong-format (DMS) GPS is corrected (#143). The user notes that GPS consistency varies by county and city; a
  per-agency GPS quality profile is measured.
- **unique_pair auto-placement ON statewide DECIDED (user, 2026-10-22, PM session):** "Turn it on everywhere."
  Evidence (#211, PR #215): +106,700 crashes (coverage ~86% → ~91%); accuracy 92.4% vs exact 90.4% on hidden police
  GPS, and 97.0% (low 96.3%) vs exact 95.7% on LAPD open data; at or above exact in D4, D6, D7, D8, D10, D11, D12, lower
  in D5 (85.2% vs 89.2%), D1/D2 too small to judge. This supersedes the "behind the 98% bar" condition for this tier only;
  street pairs that meet in more than one place still go to review. Watch D5 in the next runs.
- **OSM + TIGER street network DECIDED (user, 2026-10-22, PM session; builds the 2026-10-18 "two maps" decision):** the
  placement network is the union of OpenStreetMap and Census TIGER/Line roads, to cover streets missing or named
  differently in OSM. The user approved downloading TIGER (US Census, public domain) for California counties. Evidence
  (#211, PR #215): up to ~18,100 difficult crashes; LA open data +2.9 pts placed; SF holds (low bound 98.0% → 97.9%).
  Accuracy must be re-validated before and after; any tier change still follows the placement gate.
- **Street alias / spelling table DECIDED (user, 2026-10-22, PM session):** draft one from the #211 audit (~11,100
  difficult crashes). Per CLAUDE.md ("nothing is learned without user approval"), every entry is reviewed and approved
  by the user before the app uses it; entries carry their evidence.
- **Street aliases: top 40 APPROVED (user, 2026-10-22, PM session):** "all are right... it's the same name." The 40
  highest-impact entries of the #230 draft (review sheet `reports/testing/alias-review-2026-10-22.md`) are approved and
  copied to the live table `data/reference/street_aliases.csv` (status approved, approver and date per row). The rest
  of the draft stays proposed until the user approves it.
- **Verified typos DECIDED (user, 2026-10-22, PM session, "1 yes"):** build and measure a `verified_typo` tier (≤ 2
  edits, no rival street, the corrected pair meets at exactly one intersection, GPS agrees where present) so one-off
  typos like MAONOLIA → Magnolia don't need a human ("I don't expect a human to check it all"). It ships switched off;
  it auto-places only after Tester's measurement (#233) and the user's OK.
- **Street aliases, batch A APPROVED (user, 2026-10-22, PM session, "A"):** (1) every **abbreviation-kind** entry of the
  #230 draft (137 more, e.g. JR = Junior, EXPWY/EX = Expressway, PW/PY/PKY = Parkway, TRL = Trail, CYN = Canyon,
  HW = Highway, RT/RTE = Route) is approved, and these abbreviations plus the route-number suffix pattern ("PACIFIC COAST
  HWY - SR1", "(N)") are to become general name-cleaner rules so they work in every city; (2) every **local spelling**
  entry checked on hidden police GPS at ≥ 98% (338 entries) is approved as a batch. Entries below 98% on GPS (7) are not
  approved. Local spellings with no GPS check (390) wait for the user's review, top entries first.
- **Street aliases, the rest APPROVED (user, 2026-10-22, PM session, "approve the rest too"):** the remaining local
  spellings with no GPS check (390 entries, evidence rule: ≥ 3 crashes, ≥ 80% agreement, no rival street) are approved.
  The 7 entries that failed the hidden-GPS check (< 98%) remain unapproved. Live table: 905 entries.
- **Street aliases, last 7 APPROVED (user, 2026-10-22, PM session, "approve all"):** the 7 entries that were narrowly
  under the 98% hidden-GPS check (90.9–95.5%, e.g. ATLANTA AV → Atlantic Avenue, Long Beach) are approved too. Live
  table: all 912 draft entries.
- **Freeway crash placement (D1) DECIDED in principle (user, 2026-10-23, PM session; #246):** worked through three real
  crashes. (1) **Mainline:** start where the reference street crosses the freeway, then the stated distance in the stated
  direction along the stated-direction lanes; directions are read as written. (2) **Ramp:** at the ramp terminal on the
  reference street, plus the offset. (3) **"X TO Y":** the crash is on the connector ramp, the stated distance from Y
  along the connector (`IsFreeway = True` covers ramps and connectors). (4) **The report beats the officer's GPS** when
  they disagree; the GPS stays as provenance. Builds behind a gate; Tester measures; the user approves turning it on.
  Method and evidence: `knowledge/methods/freeway-crashes.md`.
- **Postmile in the output DECIDED (user, 2026-10-23, PM session; #248):** each placed state-highway crash gets a postmile
  looked up by code (no agent) from the public Caltrans postmile layer, marked as derived. It doesn't change placement.
- **GPS format repair statewide (PM, 2026-10-23, under the user's 2026-10-19 obvious-mistakes rule; #247):** the
  approved per-crash DMS reading (#143) applies to every agency, and a missing longitude minus is restored, each only
  when exactly one repair fits the report's roads. Measured: 4,111 + 432 crashes, chance control ≤ 1%. Whole-degree
  latitude shifts are **not** used (they fit by chance).
- **TIGER street names ON statewide DECIDED (user, 2026-10-24, PM session, "1. Yes"; #255):** the OSM + TIGER union
  (with the #243 fix) is switched on everywhere. Roads that only TIGER has stay in review (`tiger_only_auto` false).
  Evidence, run 9C: +4,965 crashes on the map (58 fatal, 374 KSI), 0 lost and 0 flipped on hidden police GPS, TIGER-name
  placements 90.9% right (Wilson low 83.1%, n=88).
- **Approximate freeway placement DECIDED (user, 2026-10-24, PM session, "2. B"; #255):** freeway crashes with no usable
  police GPS are placed by the report (the D1 method, #252) and labelled **approximate** (about 95% within 0.5 mi, a band not a bound: ~5% of mainline and ~8% of connector spots miss by more, 2.3% of mainline by over 1 mi). Evidence: mainline
  94.6% within 0.5 mi of police GPS (low 93.9%), 95.4% in the same or an adjacent Caltrans 0.5-mi segment;
  freeway-to-freeway 92.1% / 87.6%. **Not decided:** whether to drop the 2026-10-23 rule "the report beats the
  officer's GPS when they disagree". The CHP postmile tie-breaker sided with each about equally (568 vs 514), so the PM
  proposed keeping the GPS. Until the user answers, no GPS point is moved.
- **Freeway-to-freeway connectors held for review DECIDED (user, 2026-10-25, PM session; #259):** in the app,
  connector placements ("X TO Y") measured 81.5% within 0.5 mi (Wilson low 70.4%, n=65; 12% within 400 ft; run 10),
  below the 88–92% the 2026-10-24 decision was based on. They are no longer auto-placed as approximate. They go to
  review with the suggestion. Mainline and ramp crashes stay approximate. The user will review connector examples.
- **Keep the officer's GPS when it fits DECIDED (user, 2026-10-25, PM session):** "when it is in the right place and it's
  making sense, you should be going with that." When police GPS fits the report's named roads, it is used as is and
  is **not** moved to the spot the report's distance describes. This **replaces** rule 4 of the 2026-10-23 freeway
  decision ("the report beats the officer's GPS"); `freeway_move_gps` stays off. Evidence: the CHP postmile
  tie-breaker sided with the GPS and with the report about equally (568 vs 514). In the user's review of three
  freeway-to-freeway connector crashes (4630945, 1392922, 1818216), the officer GPS was right every time, and the stated
  distance and direction were loose clues (on a curving ramp, "W" is the travel direction). Unchanged: GPS that doesn't
  fit the named roads is still not used (400 ft rule), and the #218 snapped-to-intersection offset rule still applies.
- **Tabs 3–4 improvement list AGREED (user, 2026-10-25, Tabs 3–4 design session, "ok i get it. push to PM and do it"):**
  review of Crash profile and Findings on the Crenshaw study (main @ 4623ed7). Ranked, cheapest and highest value first:
  (1) show the safety tables already computed (PCF, hit-and-run/DUI/speed, left-turn vs right-angle, movement,
  conditions) #265; (2) display fixes #266; (3) findings ordered by fatal, KSI and strength, with street names and
  one-line cards #267; (4) small-number rule #271; (5) the N10 collision diagram of the finding's crashes replaces the
  autoplay replay, which plays only on tap #268; (6) tab 3 summary first, details folded, hour and day bars instead of the
  heatmap #269; (7) the 3D map fixed #272; (8) a Findings corridor summary with a map #270; (9) ranking by crash cost #273;
  (10) KSI and fatal findings #274. Later: (11) statewide-average comparison on state highways (D3, needs AADT);
  (12) LRSM countermeasure hints and before/after (v3).
- **Small numbers DECIDED (user, 2026-10-25):** a group with fewer than 10 crashes shows its count only ("1 of 6"), with
  a "too few to compare" note, never a percentage bar.
- **Tab 3 map DECIDED (user, 2026-10-25):** keep the 3D column map as the default and fix it: KSI drawn at the base
  of each column in red, so it is never hidden by property-damage crashes; the corridor fits the frame; labels on the
  top 5 locations only.
- **Ranking by crash cost DECIDED (user, 2026-10-25):** locations can be ranked by the cost of their crashes, each crash
  priced by its K/A/B/C/O level with Caltrans' published crash costs (LRSM), the same basis as HSIP B/C later. Added as
  a "Rank by cost" option; the count ranking stays. Cost values come from the current LRSM table, stored in
  `data/reference/` with the source cited, never typed from memory.
- **KSI and fatal findings DECIDED (user, 2026-10-25):** Findings adds (a) a test of whether KSI crashes are
  over-represented at a location, with the same method and thresholds as the other crash types (#34: ≥ 5 crashes at
  the location, ≥ 3 of the type, P ≥ 0.80), and (b) every fatal crash always appears as its own finding, whatever the
  statistics (fatal crashes first, 2026-10-21).
- **"X TO Y" with a local cross street placed as approximate DECIDED (user, 2026-10-25, PM session):** "when we have all
  the clues, where the crash is and everything, why are we stressing more?" A freeway report "X TO Y" whose cross
  street is a **local street** (e.g. SR-60 W/B TO I-10 / EUCLID AVENUE / 55 ft W, record 4630945) describes a crash on
  X's main lanes: the local street passes under or over X. With no usable GPS, it is placed automatically as
  **approximate**, measured along X from that street (#259), like other mainline crashes. Only true connector reports,
  where the cross street is X or Y itself, stay in review (2026-10-25 decision). Evidence before the #259 fixes (Tester,
  seed-246 sample): all "X TO Y" placements 53 of 65 (81.5%, Wilson low 70.4%) within 0.5 mi; the local-street subgroup
  132 reports, 39 placed by the old connector logic, 34 of those within 0.5 mi (87%, small n). Tester re-measures the
  new rule on the fixed code.
- **House-address crashes (D5) DECIDED (user, 2026-10-25, PM session, "B"; #264):** a crash whose report gives a house
  address instead of a cross street is placed at the matching **USDOT National Address Database (NAD)** address point
  where NAD covers the area, with provenance `address_nad`. NAD is public domain; it has 10 CA contributors (San
  Bernardino, Sacramento, Ventura, Solano, Santa Cruz, Merced, Shasta, Santa Barbara, Stockton, Costa Mesa). Elsewhere
  the crash goes to **review**, with the Census Geocoder / TIGER address-range point as the suggestion. Evidence (Tester,
  PR #277): NAD 86.1% within 400 ft of police GPS (Wilson low 84.4%), 74.3% within 250 ft, 647 of 12,568 D5 crashes;
  Census 64.7% and TIGER 65.4% within 400 ft. NAD placements are mid-block address points, so they count on segments and
  never at an intersection. Because 86% is below the 98% bar for precise placement, they are labelled **approximate**
  ("usually within 400 ft"), like the freeway approximate placements, and counted on the approximate side of coverage.
  (PM, applying the existing 98% rule; the user may revisit.)
- **Railway and trail crossings, and mile markers, as places (D3) DECIDED (user, 2026-11-01, PM session):** from the
  D3 no-GPS walkthrough (20 crashes, 10 fatal).
  - **Railways and trails:** a report naming a street and a railway ("FRANCIS ST & RAIL ROAD") or a trail or bike path
    ("MANGO AVE & PACIFIC ELECTRIC TRL") is placed **where the street crosses the railway or trail**. A stated distance
    ("817 ft W of CITRUS AV" on "ESCONDIDO CREEK BIKE PATH") is measured from that crossing **along the path, in the
    stated direction**. Two or more possible crossings in the agency's area → review list, never the nearest guess. The
    user: the crash happens at the crossing whatever the vehicle, and which lane (bike lane, shared lane) doesn't
    matter. Where the "path" is a bike lane on the road itself, the road is used. **Pending the user's confirmation:** a separate bike-only path is placed on the path itself (the user said "that's
    different"; the PM reads it as placed on the path, not on a road). Until confirmed, those crashes go to review with
    the path spot as the suggestion. Railway
    and path lines come from the same OSM extract (railway=rail/light_rail, highway=cycleway/path/footway with a
    name), with TIGER rail features where OSM lacks them.
  - **Mile markers:** "ANGELES CREST HWY & MILE MARKER 28.86" is placed at that **Caltrans postmile** on the named
    state route (the postmile layer, #248), plus any stated offset. A named state highway is mapped to its route
    (Angeles Crest Hwy = SR-2) through the postmile layer or the OSM ref; the county comes from the crash's county code,
    not the reporting city; CHP writes the number without Caltrans' R/M prefix, so a postmile that exists under two
    prefixes is two places → review. The user: "we have got [an] extra clue".
  - Both are built behind a switch, measured by Tester on hidden police GPS (crashes that have both), and switched on
    with the user's OK, like every new tier. If they reach the 98% bar they auto-place as precise; otherwise the user
    decides whether they're labelled approximate. With zero misses, a Wilson 95% low of 98% needs at least 189 truth
    crashes; with fewer, Tester reports the numbers and the user decides.
- **State-highway crash rates from Caltrans AADT DECIDED (user, 2026-10-26, PM session, "BUILD IT"):** exposure for
  crash rates on the State Highway System comes from the **Caltrans Traffic Census Program**: AADT by route, county and
  postmile (back/ahead legs), plus truck AADT by axle class and ramp volumes by district. Annual .xlsx files, and the
  ArcGIS layers CHhighway/Traffic_AADT (14,080 points) and Truck_Volumes_AADT (6,865). Each crash joins through its
  derived postmile (#248). The tool shows:
  - per segment: crashes per million vehicle-miles (fatal, fatal + injury, all);
  - ramps: crashes per million vehicles;
  - truck-involved crash rates using 3+ axle truck AADT;
  - each compared with (1) Caltrans' statewide average for the same highway type, once its published source is
    confirmed, (2) the corridor's own average, and (3) year over year.

  The AADT year and source are cited on every row, and findings cite the rate table. Any comparison with Caltrans
  averages uses Caltrans' on-highway counting rule or is labelled approximate. This settles the "rate exposure" part of
  #34 for state highways. Local streets still need local counts.
- **Caltrans rate groups for statewide-average comparison DECIDED (user, 2026-10-29, PM session; #294):** "either the
  engineer enters, or the engineer can attach a file. If that is a file, you can read it." For each state-highway
  segment, intersection and ramp, the rate group comes from the engineer in one of two ways:
  (1) **entered** in the app from Caltrans' published list ("Basic Average Crash Rate Table", *2024 Crash Data on
  California State Highways*: highways H01–H67 pp. 83–85, intersections I01–I31 pp. 86–87, ramps R01–R80 pp. 88–90;
  rates "loaded into TSN on April 22, 2022"; the ADT factor is "/" (divided by ADT in thousands) or "*" (times ADT in
  thousands), per row; stored in `data/reference/` with the citation);
  (2) **read from the Caltrans TASAS output the engineer attaches** (the PDF a district returns for a crash-data
  request, e.g. Table B with rate groups and average rates).
  The file is read by **code** (a deterministic parser), never by AI: every number shown is traceable to the file or to
  the published table. Whatever can't be parsed is shown for the engineer to enter. CrashIQ then computes the expected
  rate (base rate + ADT factor) and the comparison. Nothing is guessed: no rate group, no statewide comparison. This **replaces** the user's earlier answer "B" (2026-10-26, Engineering chat, on #294, never recorded in docs/03).
  A map-data suggestion may still pre-fill the field, but only as a labelled suggestion the engineer confirms. Comparisons use Caltrans' on-highway counting rule
  or are labelled approximate.
- **Ramp identification and ramp rates DECIDED (user, 2026-10-30, Engineering session; #300):** option **B**, "A +
  engineer picks". A crash's ramp is identified when its report names a ramp (ON/OFF RAMP, ONR/OFR), its direction of
  travel and its cross street, and **exactly one** Caltrans ramp row (district ramp ADT file) within 0.3 mi on the same
  route and county matches all three (direction, on/off, cross street in the description). When 2 or more rows fit,
  the review list offers them and the engineer picks one (approved once, like an alias). Otherwise the crash gets no
  ramp rate, with a note. Ramp ADT is the latest count at or before the crash year, labelled with its year, never a
  later one; District 7's placeholder values (1001, 999) count as missing. Shown as a **"Ramps" table on tab 3** for
  state-highway studies: one row per identified ramp with crashes, ramp ADT and crashes per million vehicles; the
  small-number rule applies.
- **Which crashes count in a state-highway mainline crash rate DECIDED (user, 2026-10-31 and 2026-11-01, PM session;
  #297):** "only mainline taken as mainline", then "1a, 2a, 3 ok" to the three follow-up questions. This is about
  **counting for rates only**: where a crash is placed on the map doesn't change (freeway rules 2026-10-23/25,
  approximate tiers).
  - **In the segment (mainline) rate:** every crash on the highway's own roadway. On a conventional (at-grade) state
    highway this **includes crashes at its intersections** (answer 2a), including reports that name the cross street
    as the primary road and the highway second, when the crash is at the intersection (answer 3). **"At the
    intersection" = within the study's intersection influence radius (default 250 ft)**, the same HSM rule the app uses for intersection
    crashes everywhere (§3 above; user 2026-11-01, "2A"). Beyond that radius on the cross street, it's out.
    A **blank distance counts as 0** (user 2026-11-01, Engineering session). So a cross-street-primary crash is at
    the intersection when its distance is blank or no more than the study's influence radius (default 250 ft).
    **Which segment gets an intersection's crashes** (user 2026-11-01, Engineering session): an intersection sits
    where two segments meet. Its crash goes to the segment on the side its GPS is on. A crash with no GPS, placed at
    the intersection itself, goes to the segment after it in station order (PM, applying the same rule to edge cases:
    a GPS whose position along the corridor is within 25 ft of the intersection's own station counts as at the
    station, since that side is GPS noise; the last intersection, which has no segment after it, gives its crashes
    to the segment before it). Distances given in miles are converted to feet before comparing with the radius.
    Intersection rates (Caltrans groups I01–I31, #294) may be shown as a separate view of those intersections; they
    are never added to the segment rate.
  - **Out of the mainline rate, into the ramp rates (#300):**
    - reports that name a ramp (ON/OFF RAMP, ONR/OFR);
    - police wording "<route> <dir> TO <local street>" as the road, with no ramp word: the **<dir> off-ramp to that
      street** (answer 1a). For #300's strict match it counts as naming the ramp: direction <dir>, off, cross street =
      that street;
    - true connectors "<route> TO <route>" whose cross street is one of the two routes (2026-10-25).
  - **Stays mainline:** "<route> TO <route>" with a **local** cross street (2026-10-25: the local street passes under
    or over the freeway).
  - **Out of the rate entirely:**
    - crashes on a cross street or frontage road away from the highway (beyond the study's influence radius on a
      conventional highway), even
      when their GPS sits on or next to the highway line;
    - on a freeway (access-controlled), any crash whose primary road is a cross street;
    - roads over or under a freeway (N7, #67).
  - **Why:** this follows Caltrans' TASAS mainline/ramp split, so mainline rates are comparable with Caltrans' highway
    base rates (#294). It replaces the interim "segment crashes only" label on #296.
- **Ramp count age and direction DECIDED (user, 2026-11-01, Engineering session; #302):**
  - **Count age:** a ramp count more than **5 years older** than the year it stands for isn't used (a 5-year-old count
    is). The ramp's row is checked for every study-window year: if any window year has only a count that's too old,
    the row gets **no rate** (all or nothing per row) and gives the reason "count too old for <years> (newest <year>)";
    its crash counts are still shown. How many identified ramp crashes this affects is to be measured on #302's merged
    code (Engineering's first estimate also counted 5-year-old counts, which are used).
  - **Direction: matched strictly, no translation (user, 2026-11-01 later the same day, PM session: "do not do it. It will bite us in
    the butt").** This **replaces** the earlier 2026-11-01 answer (Engineering session) to translate compass and route directions (a CHP "S/B" on a
    route Caltrans signs EB/WB). A ramp crash whose reported direction doesn't match the ramp row's direction as
    written gets no ramp rate, with the reason. #308 is closed unbuilt.
