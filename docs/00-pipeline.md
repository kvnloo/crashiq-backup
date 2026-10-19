# CrashIQ — pipeline and skills per stage

Conductor: `new-tool` (yours). Each stage has a lead skill plus helpers. A stage ends when its gate artifact exists.
Skills live in ~/.claude/skills. Roles (PM session, engineer session) and rules: `CLAUDE.md`.

| Stage | Lead + helpers | Extra checks | Gate | Status |
|---|---|---|---|---|
| 1 Kickoff | product-kickoff | — | docs/01-kickoff.md | done |
| 2 Requirements | grill-me, brainstorming, prompt-me | — | docs/03-requirements.md (locked) | done |
| 3 Design | ai-agent-validation, oracle-spine, caltrans-traffic-expert, architecture-design, ux-design | — | docs/04-design.md | done (F1 open) |
| 4 Build | fastapi-react-builder, backend-build, frontend-build, web-design, viz-design, tdd, karpathy-guidelines | xlsx + pdf: the exports · subagent-driven-development | schemas + happy-path run end to end | **in progress** |
| 5 Test | tool-testing, testing-strategy, code-review | run: click through the app and find bugs · security-review · systematic-debugging · model bake-off scoring | six-condition testing gate | — |
| 6 Oracle onboard | oracle-spine | — | context object round-trip with provenance | — |
| 7 Ship | ship-it, deploy-checklist | — | pre-ship checklist passes | — |
| Paid launch | system-design, ship-it | security test before charging money | accounts + billing + spend caps + terms | — |

Cross-cutting: GitHub after every step, refresh if a session drifts, model bake-off (proposed new skill).

**From Stage 4 on, work runs through GitHub:** the PM session turns the design into issues → the engineer session
builds one issue per branch, opens a PR and merges it once tests pass (user decision on #2) → the PM session reviews;
review comments become follow-up issues.

## Stage 4 status (2026-10-18)
- Merged: study setup, corridor network, CCRS ingest + hardening, crash placement, crash profile + 3D map
  controls (#43), over-representation screen (#41, #50), critical rate (#60), exports (#33),
  methods & references (#56), the #34 defaults (#58).
- Open PRs, stacked, merge in order: #36 (fix #35, no-GPS cities) → #40 (3D column map, #38) → #46 (#45 findings
  without AI). #49 was decided as strict, which is what #46 does.
- Waiting on the user: #39 (crashes whose cross street isn't on the corridor). #34 items 2, 4, 6 parked with #55.
- Next build issues: #52 safety tables, #53 placement checks, #54 long-corridor performance, #37 setup screen
  layout, #55 AI guardrails (needs the API key), #19 state pack.
- PM work carried over from Hermes: #2, #4, #18, #20.

## User direction log
- **2026-10-18 (user, via Claude Code):** methodology correctness comes first. The mockup layout
  (`design/mockups/`) is approved in direction and will be refined later.
- **2026-10-18 (user, in the PM session):** Hermes is retired. A Claude Code PM session takes over everything Hermes
  did (issues, reviews, `docs/`, research); decisions are asked in that chat instead of over WhatsApp.
