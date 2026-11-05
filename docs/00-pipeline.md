# CrashIQ — pipeline and skills per stage

Conductor: `new-tool` (yours). Each stage has a lead skill plus helpers. A stage ends when its gate artifact exists.
**Yours** = ~/.claude/skills (Hermes reads them too). **Hermes built-in** = bundled (B) or optional, installed on demand (O).

| Stage | Yours: lead + helpers | Hermes built-in that adds something | Gate | Status |
|---|---|---|---|---|
| 1 Kickoff | product-kickoff | spike (B) | docs/01-kickoff.md | done |
| 2 Requirements | grill-me, brainstorming, prompt-me | decision-questionnaire (O) | docs/03-requirements.md (locked) | done |
| 3 Design | ai-agent-validation, oracle-spine, caltrans-traffic-expert, architecture-design, ux-design | architecture-diagram (B): picture of the system | docs/04-design.md | done (F1 open) |
| 4 Build | fastapi-react-builder, backend-build, frontend-build, web-design, viz-design, tdd, karpathy-guidelines | claude-code (B): hand big coding jobs to Claude Code · test-driven-development (B) · xlsx + pdf (B): the exports · subagent-driven-development (O) | schemas + happy-path run end to end | done (frozen 2026-11-02) |
| 5 Test | tool-testing, testing-strategy, code-review | dogfood (B): click through the app and find bugs · requesting-code-review (B): security scan · systematic-debugging (B) · adversarial-ux-test (O) · evaluation (O): model bake-off scoring | six-condition testing gate | done except #360 (2026-11-02) |
| 6 Oracle onboard | oracle-spine | — | context object round-trip with provenance | — |
| 7 Ship | ship-it, deploy-checklist | github (B) · docker-management (O) | pre-ship checklist passes | — |
| Paid launch | system-design, ship-it | stripe-projects / stripe-link-cli (O): payments · web-pentest (O): security test before charging money | accounts + billing + spend caps + terms | — |

Overlaps, pick one: grill-me (yours) = grill-me (O); tdd (yours) ≈ test-driven-development (B); code-review (yours)
≈ requesting-code-review (B). Use yours as lead (they encode your conventions), built-ins as extra checks.
Cross-cutting: github after every step, refresh if a session drifts, model bake-off (proposed new skill).

**From Stage 4 on, work runs through GitHub:** PM turns the design into issues → Engineering builds one issue per branch
and opens a PR → PM reviews and merges once the review is clean and tests pass → Tester tests data and screens
independently and files `bug` issues with a failing test, which go round the same loop. Ownership and rules: `CLAUDE.md`.
(Hermes ran this until 2026-10-18; the "Hermes built-in" column is history.)

## User direction log
- **2026-11-02 (user, PM chat): one TrafficIQ suite agent, later.** All tools will sit on the TrafficIQ website with
  one agent for the whole suite (not a CrashIQ-only bot). Its first CrashIQ job: read messy crash locations on the
  review list and suggest which real streets were meant; code places the crash, the engineer accepts or rejects,
  accepted readings become alias rules. Tested on hidden-GPS / LAPD truth before it is shown. Comes after shipping,
  after the cheaper rule fixes, and after the #55 guardrails. Rules and lesson sources: trafficiq `docs/AGENT.md`.
  **Keep writing `knowledge/lessons.md`**: it is the agent's starting knowledge.
- **2026-10-18 (user, via Claude Code):** methodology correctness comes first. The mockup layout
  (`design/mockups/`) is approved in direction and will be refined later.
- **2026-10-19 (user):** PM merges clean, tested PRs. A Tester session joins (docs/03 log).
- **2026-11-02 (user, PM session): build frozen; move to testing and shipping.** "finish the 5 PRs, park fine-tuning,
  move to testing and shipping". The four open feature PRs (#310, #315, #339, #354) and docs PR #348 finish through the
  normal review loop. Remaining fine-tuning and research issues are labelled `backlog` and wait until after shipping
  (placement refinements, extra measurements, state pack, nationwide research, #287 part 2, #52). The merged
  features behind switches (#322 mile markers at postmiles, #324 railway/trail crossings) ship with their switches off. Stage 5 (Test) starts
  against the six-condition gate; Stage 7 (Ship) follows. The user is asked only for big decisions from here on.
- **2026-11-02 (user, PM session): shipping waits for the HSM golden case.** Stage 5 ended with 5 of 6 gate conditions
  passing and the 3-corridor click-through 3/3 (`reports/testing/stage5-2026-11-02.md`). Asked whether to ship with
  #360 (the HSM Ch. 4 critical-rate published example) as a known gap or wait, the user said: "Wait." Stage 7 (Ship)
  starts only after the user supplies the example and its golden test passes.
- **2026-11-02 (user, PM session): the #360 golden case is Oregon DOT's worked example.** The PM proposed ODOT
  *Analysis Procedures Manual v2*, Ch. 4, Example 4-3 ("HSM Critical Rate for Intersections with Internal Reference
  Population", pp. 4-27 to 4-32), which applies the HSM 1st ed. Ch. 4 critical-rate equation, in place of the HSM
  pages. Asked "Use Oregon DOT's Example 4-3 as the published check instead of the HSM pages?", the user said:
  "Yes, use it". Stage 7 (Ship) starts once that golden test passes.
