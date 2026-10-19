# CLAUDE.md — CrashIQ

Read by every agent working in this repo. Two Claude Code sessions share it:
- **PM session** (leads the pipeline; took over from Hermes on 2026-10-18): plans, writes issues, reviews PRs, keeps `docs/`.
- **Engineer session** (writes the code): builds one issue at a time.

Hermes is retired. Older issues, docs and reports that say "Hermes" mean the PM role.

## Start here
1. `git pull` before you start. Push when you finish.
2. Read `docs/03-requirements.md` (locked) and `docs/04-design.md` before touching code.
3. Current pipeline stage: the table in `docs/00-pipeline.md`.

## Who owns what
| Area | Owner | Others |
|---|---|---|
| `docs/`, `reports/`, `research_notes/`, `knowledge/` | PM session | Engineer session proposes changes in a PR comment or issue, never edits directly |
| `backend/`, `frontend/`, `tests/`, build/config files | Engineer session | PM session reviews PRs; asks for changes via review comments or issues |
| `CLAUDE.md`, `.github/` | Shared | Change only with the user's OK |

## How work moves
- **Tasks are GitHub issues** (template: `.github/ISSUE_TEMPLATE/task.md`). The PM session writes them from the
  design docs. Labels: `task` + `claude-code` for build work, `pm` for PM work (research, docs).
- **The engineer session does one issue per branch** (`feat/<issue#>-<slug>`), tests first, then opens a PR with `Closes #<n>`.
- **The PM session reviews** the PR against the issue's acceptance criteria and the docs.
- **Merging (Stage 4, user decision on #2):** the engineer session merges its own PR once tests pass, so the next
  issue can build on it. The PM session and the user can review after merge; review comments become follow-up issues.
- The repo is the only shared memory. A decision that isn't written in `docs/` hasn't been made.
  An agent's private memory doesn't count.
- **Decisions come from the user only.** Agents propose, the user decides. The PM and engineer sessions are both
  Claude: neither approves the other's decisions or work as a stand-in for the user.
- If code needs a decision the docs don't cover: stop, open an issue labelled `decision-needed`, don't guess.
  The PM session asks the user **in its chat** (one question at a time, options plus a recommendation), then records
  the answer in `docs/` and on the issue. Only then does work continue.
- Review loops are capped: at most 3 PM ↔ engineer rounds per PR, then it goes back to the user.

## Non-negotiable rules
- **Code computes every number.** AI (Claude, Jev) never produces a number that reaches the user. The validator
  rejects any finding whose numbers aren't in a cited table.
- **Provenance on everything:** every crash location (`gps/exact/fuzzy/jev(p)/user/unmatched`) and every finding.
- **Nothing is learned without user approval** (worked examples, pattern library, alias table).
- **Runtime AI:** Claude API tool-use loop behind the swappable agent contract; Jev only at the seams in `04-design.md`.
  API keys server-side only (`ANTHROPIC_API_KEY`, `TYPESAFE_API_KEY`), never committed.
- Stack: FastAPI + Vite/React + Leaflet, reusing the DemandIQ shell. SQLite locally.

## Commands
First time: `make setup` (Python venv in `.venv/` + `npm ci` in `frontend/`).
| Task | Command |
|---|---|
| Run backend (API on :8000, auto-reload) | `make backend` |
| Run frontend (app on :3000, proxies `/api` to :8000) | `make frontend` |
| Run all tests (no network) | `make test` |
| Lint (ruff + eslint) | `make lint` |
| Production build served by one process on :8000 | `make serve` |
