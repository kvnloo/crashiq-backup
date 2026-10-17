# CLAUDE.md — CrashIQ

Read by every agent working in this repo: Claude Code (writes the code) and Hermes (leads the pipeline).

## Start here
1. `git pull` before you start. Push when you finish.
2. Read `docs/03-requirements.md` (locked) and `docs/04-design.md` before touching code.
3. Current pipeline stage: the table in `docs/00-pipeline.md`.

## Who owns what
| Area | Owner | Others |
|---|---|---|
| `docs/`, `reports/`, `research_notes/` | Hermes | Claude Code proposes changes in a PR comment or issue, never edits directly |
| `backend/`, `frontend/`, `tests/`, build/config files | Claude Code | Hermes reviews PRs; asks for changes via review comments or issues |
| `CLAUDE.md`, `.github/` | Shared | Change only with the user's OK |

## How work moves
- **Tasks are GitHub issues** (template: `.github/ISSUE_TEMPLATE/task.md`). Hermes writes them from the design docs.
- **Claude Code does one issue per branch** (`feat/<issue#>-<slug>`), tests first, then opens a PR with `Closes #<n>`.
- **Hermes reviews** the PR against the issue's acceptance criteria and the docs. The user merges.
- The repo is the only shared memory. A decision that isn't written in `docs/` hasn't been made.
  An agent's private memory doesn't count.
- **Decisions come from the user only.** Agents propose, the user decides. Agents never approve each other's
  decisions or work as a stand-in for the user.
- If code needs a decision the docs don't cover: stop, open an issue labelled `decision-needed`, don't guess.
  Hermes asks the user over **WhatsApp** (Hermes gateway), then records the answer in `docs/` and on the issue.
  Only then does work continue.
- Review loops are capped: at most 3 Hermes ↔ Claude Code rounds per PR, then it goes back to the user.

## Non-negotiable rules
- **Code computes every number.** AI (Claude, Jev) never produces a number that reaches the user. The validator
  rejects any finding whose numbers aren't in a cited table.
- **Provenance on everything:** every crash location (`gps/exact/fuzzy/jev(p)/user/unmatched`) and every finding.
- **Nothing is learned without user approval** (worked examples, pattern library, alias table).
- **Runtime AI:** Claude API tool-use loop behind the swappable agent contract; Jev only at the seams in `04-design.md`.
  API keys server-side only (`ANTHROPIC_API_KEY`, `TYPESAFE_API_KEY`), never committed.
- Stack: FastAPI + Vite/React + Leaflet, reusing the DemandIQ shell. SQLite locally.

## Commands
To be filled in when Stage 4 scaffolds the app (test, lint, run backend, run frontend).
