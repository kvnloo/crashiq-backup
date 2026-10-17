# CrashIQ — pipeline and skills per stage

Conductor: `new-tool`. Each stage has one lead skill plus helpers. A stage ends when its gate artifact exists.

| Stage | Lead skill | Helpers | Gate | Status |
|---|---|---|---|---|
| 1 Kickoff | product-kickoff | spike | docs/01-kickoff.md | done |
| 2 Requirements | grill-me | brainstorming, prompt-me | docs/03-requirements.md (locked) | done |
| 3 Design | ai-agent-validation, oracle-spine | caltrans-traffic-expert (mode formats), architecture-design, ux-design | docs/04-design.md | done (F1 open) |
| 4 Build | fastapi-react-builder | backend-build, frontend-build, web-design (DemandIQ look), viz-design (dashboard charts), tdd, karpathy-guidelines | contract (schemas) + happy-path run end to end | next |
| 5 Test | tool-testing | testing-strategy, code-review, requesting-code-review (security scan) | six-condition testing gate | — |
| 6 Oracle onboard | oracle-spine | — | context object round-trip with provenance | — |
| 7 Ship | ship-it | deploy-checklist, github | pre-ship checklist passes | — |
| Paid launch (after 7) | ship-it | system-design (accounts, payments, limits) | accounts + billing + spend caps + terms | — |

Cross-cutting: `github` (push after every step), `systematic-debugging` when something breaks,
`refresh` if a session drifts, model bake-off (proposed new skill) before picking the Claude tier.
