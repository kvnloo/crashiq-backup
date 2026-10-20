# CLAUDE.md — CrashIQ

Read by every Claude Code session working in this repo. Since 2026-10-18 Claude Code does all the work (Hermes is
retired, user's decision). Several sessions can run at once (e.g. one per issue, started from the desktop app or phone
via Remote Control); these rules keep them from colliding.

Standing sessions (user decisions, 2026-10-18/19):
- **PM:** writes issues from the design docs, reviews PRs, records decisions in `docs/`, merges.
- **Engineering:** builds one issue per branch and fixes bugs.
- **Tester:** independent data and screen testing. Never changes app code (`backend/`, `frontend/`); its own test code
  and reports go through a PR like everything else.

## Start here
1. `git pull` before you start. Push when you finish.
2. Read `docs/03-requirements.md` (locked) and `docs/04-design.md` before touching code.
3. Current pipeline stage: the table in `docs/00-pipeline.md`.

## Who owns what
| Area | Owner | Rule |
|---|---|---|
| `backend/`, `frontend/`, `tests/`, build/config files | Claude Code | Changes only through a PR |
| `docs/`, `reports/`, `research_notes/`, `knowledge/` | Claude Code | Changes only through a PR; decisions are recorded only after the user makes them |
| `CLAUDE.md`, `.github/` | Shared | Change only with the user's OK |

## How work moves
- **Tasks are GitHub issues** (template: `.github/ISSUE_TEMPLATE/task.md`), written from the design docs.
- **One session = one issue = one branch** (`feat/<issue#>-<slug>`), in its own git worktree when other sessions are
  running. Before starting, check the issue isn't already claimed; claim it with a comment ("taken by session <name>").
- Tests first, then a PR with `Closes #<n>`.
- **Review:** a different session (not the one that wrote the code) reviews the PR against the issue's acceptance
  criteria and the docs, and posts the review as a PR comment.
- **Merging (user decision, 2026-10-19):** the PM session merges a PR once its review is clean and tests pass. The user
  isn't the merge step. Anything that needs a user decision (an open `decision-needed` issue, a change to methods or
  rules) waits for the user's answer before merging.
- The repo is the only shared memory. Sessions don't see each other's chats; anything another session needs goes in the
  issue, the PR or `docs/`. A decision that isn't written in `docs/` hasn't been made.
- **Decisions come from the user only.** Sessions propose, the user decides. A session never approves another session's
  decision or work as a stand-in for the user.
- If code needs a decision the docs don't cover: stop, open an issue labelled `decision-needed`, ask the user in chat, don't
  guess. When the user answers, record it in `docs/` and on the issue. Only then does work continue.
- Review loops are capped: at most 3 review rounds per PR, then it goes back to the user.
- **Bugs:** Tester files each one as an issue labelled `bug`, with a failing test that shows it. Engineering fixes it,
  PM reviews and merges, Tester re-verifies and closes it (or reopens it with what still fails).

## Isolation (after the 2026-10-18 SQLite -wal corruption)
- Every session works in its own git worktree. Never switch branches or stash in a checkout whose `data/` another
  session's server is using.
- Tester uses its own database copy, `data/tester.sqlite` (never the shared `data/crashiq.sqlite`), and its own ports:
  API 8001, app 3101.
- TIMS: the user signs in in the browser pane. No login bot, and no session ever types or stores a password.
- Screen tests are scripted (no AI steps), with telemetry off.

## Cost
- Agent work runs on the user's Max plan only. No API-key billing, no extra-usage credits, no paid agent gateways.
- Ask the user before fanning out parallel sub-agents (they use plan limits faster).

## Non-negotiable rules
- **Code computes every number.** AI (Claude, Jev) never produces a number that reaches the user. The validator
  rejects any finding whose numbers aren't in a cited table.
- **Provenance on everything:** every crash location (`gps/exact/fuzzy/jev(p)/user/unmatched`) and every finding.
- **Nothing is learned without user approval** (worked examples, pattern library, alias table).
- **Runtime AI (the product's analyst, parked with #55):** Claude API tool-use loop behind the swappable agent contract;
  Jev only at the seams in `04-design.md`. API keys server-side only (`ANTHROPIC_API_KEY`, `TYPESAFE_API_KEY`), never
  committed. Off until the user approves the cost.
- Stack: FastAPI + Vite/React + Leaflet/MapLibre, reusing the DemandIQ shell. SQLite locally.

## Commands
First time: `make setup` (Python venv in `.venv/` + `npm ci` in `frontend/`).
| Task | Command |
|---|---|
| Run backend (API on :8000, auto-reload) | `make backend` |
| Run frontend (app on :3000, proxies `/api` to :8000) | `make frontend` |
| Run all tests (no network) | `make test` |
| Lint (ruff + eslint) | `make lint` |
| Production build served by one process on :8000 | `make serve` |
