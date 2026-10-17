# CrashIQ — pipeline and skills per stage

Conductor: `new-tool` (yours). Each stage has a lead skill plus helpers. A stage ends when its gate artifact exists.
**Yours** = ~/.claude/skills (Hermes reads them too). **Hermes built-in** = bundled (B) or optional, installed on demand (O).

| Stage | Yours: lead + helpers | Hermes built-in that adds something | Gate | Status |
|---|---|---|---|---|
| 1 Kickoff | product-kickoff | spike (B) | docs/01-kickoff.md | done |
| 2 Requirements | grill-me, brainstorming, prompt-me | decision-questionnaire (O) | docs/03-requirements.md (locked) | done |
| 3 Design | ai-agent-validation, oracle-spine, caltrans-traffic-expert, architecture-design, ux-design | architecture-diagram (B): picture of the system | docs/04-design.md | done (F1 open) |
| 4 Build | fastapi-react-builder, backend-build, frontend-build, web-design, viz-design, tdd, karpathy-guidelines | claude-code (B): hand big coding jobs to Claude Code · test-driven-development (B) · xlsx + pdf (B): the exports · subagent-driven-development (O) | schemas + happy-path run end to end | next |
| 5 Test | tool-testing, testing-strategy, code-review | dogfood (B): click through the app and find bugs · requesting-code-review (B): security scan · systematic-debugging (B) · adversarial-ux-test (O) · evaluation (O): model bake-off scoring | six-condition testing gate | — |
| 6 Oracle onboard | oracle-spine | — | context object round-trip with provenance | — |
| 7 Ship | ship-it, deploy-checklist | github (B) · docker-management (O) | pre-ship checklist passes | — |
| Paid launch | system-design, ship-it | stripe-projects / stripe-link-cli (O): payments · web-pentest (O): security test before charging money | accounts + billing + spend caps + terms | — |

Overlaps, pick one: grill-me (yours) = grill-me (O); tdd (yours) ≈ test-driven-development (B); code-review (yours)
≈ requesting-code-review (B). Use yours as lead (they encode your conventions), built-ins as extra checks.
Cross-cutting: github after every step, refresh if a session drifts, model bake-off (proposed new skill).
