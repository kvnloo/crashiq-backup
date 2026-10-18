# CrashIQ knowledge base

The user's rule (2026-10-18): **every lesson is a golden nugget.** Anything learned about crash data
(finding it, pulling it, cleaning it, placing it, validating it, organizing it) is written here, so every
agent and future session starts from what we already know instead of rediscovering it. This folder is
meant to become the "crash data guru" skill.

| Folder | What goes in it |
|---|---|
| `sources/` | One file per data source: where it is, how to pull it, its fields, quirks, cleaning rules, licence |
| `methods/` | How we do a job (geocoding, assignment, rates…): the method, its measured accuracy, what failed |
| `lessons.md` | Dated one-line lessons, newest first. Every session adds to it |
| `pain-points.md` | Every data problem as a client pain point: evidence, cost to the client, how CrashIQ fixes it. Pitch + roadmap source |

Rules for writing here:
- Lessons carry **evidence** (a count, a test result, a record id) and a **date**.
- Write what *failed* too. A dead end recorded saves a night of work.
- If a lesson changes a requirement or a design decision, it still needs the user's decision in `docs/`.
  This folder records knowledge; it doesn't make decisions.
