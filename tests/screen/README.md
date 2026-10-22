# Screen tests (Tester)

Scripted tests of CrashIQ in a real browser: Setup, Corridor (including drawing the line on the map), Crash profile
(key numbers, data quality, road users), its review list (fatal crashes first, #175), and phone (375 px) and tablet (768 px) widths.
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

At phone widths the tests check no sideways
scroll and that the key-number tiles stay on screen without overlapping; other overlaps are not checked.
Live recording: `npm run test:live` runs the `Live:` tests on the real Crenshaw rows (tests/fixtures/live) with a
second app on :3101 (the Tester's other port): the review list's place, exclude and undo flow.

Results: `.e2e/results/<test>/trace.md` with a screenshot at any failure.
