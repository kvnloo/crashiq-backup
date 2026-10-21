# Screen tests (Tester)

Scripted tests of CrashIQ tabs 1-2 in a real browser: Setup, Corridor, Crash profile and its review list.
Framework: [TesterArmy e2e](https://github.com/tester-army/e2e) 0.21.2 with the web engine (Playwright Chromium),
**exact steps only** (no agent steps, no model) and **telemetry off** (`E2E_TELEMETRY_DISABLED=1`, `DO_NOT_TRACK=1`,
and `e2e telemetry disable` on this machine).

```bash
cd tests/screen && npm ci && npm test
```

What a run does:
- `make_fixtures.py` copies the app's offline Crenshaw data (`tests/fixtures`) and takes GPS and cross street off three
  crashes, so the review list has something to show.
- The run starts its own app on **:8001** (Tester port): the built frontend (`make build` first) served by the backend,
  on a fresh Tester-only database `data/tester_screen.sqlite`, in offline fixture mode. No network: the map's tile
  requests are blocked.
- Every number the screen shows is checked against the app's own API for the same study.

Not covered yet: drawing a corridor by clicking the map (the tests set the line through the API), phone widths.
Results: `.e2e/results/<test>/trace.md` with a screenshot at any failure.
