// Tester's screen tests on the LIVE Crenshaw recording (tests/fixtures/live: real CCRS rows, real no-GPS crashes),
// second app on :3101 (the Tester's other port). Run: npm run test:live. Otherwise as e2e.config.ts.
// Tester's screen tests (CrashIQ tabs 1-2). Exact steps only: no agents, no model, telemetry off (package.json).
// The run starts its own app on :8001 (the Tester port): the built frontend served by the backend, on a fresh
// Tester-only database, in the app's offline fixture mode (recorded Crenshaw OSM + CCRS, no network).
import { resolve } from 'node:path';
import type { E2EConfig } from 'e2e';
import { web } from '@e2e-dev/web';

const repo = resolve(import.meta.dirname, '../..');
const python = process.env.CRASHIQ_PYTHON ?? resolve(repo, '../Crash/.venv/bin/python');

export default {
  targets: [
    {
      name: 'live',
      engine: web({ viewport: { width: 1440, height: 900 } }),
      app: {
        url: 'http://127.0.0.1:3101',
        readyUrl: 'http://127.0.0.1:3101/health',
        command: {
          executable: python,
          args: ['-m', 'uvicorn', 'crashiq.server:_default_app', '--factory', '--app-dir', resolve(repo, 'backend'),
                 '--port', '3101'],
          env: {
            CRASHIQ_DB: resolve(repo, 'data/tester_screen_live.sqlite'),
            CRASHIQ_FIXTURES_DIR: resolve(repo, 'tests/fixtures/live'),
            DO_NOT_TRACK: '1',
          },
          log: '.e2e/logs/app-live.log',
        },
      },
    },
  ],
} satisfies E2EConfig;
