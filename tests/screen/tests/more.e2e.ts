// Tester screen tests, part 2 (#177): drawing a corridor on the map, phone and tablet widths, and the road-user
// section (pedestrians, bicyclists, e-bikes, e-scooters, motorcyclists). Exact steps only, no model.
import { expect } from 'e2e';
import { test } from '@e2e-dev/web';

const LINE = [[33.8953, -118.32662], [33.9040, -118.32662], [33.9123, -118.32662]];
const CENTER = [33.9038, -118.3266];   // CorridorMap's DEFAULT_CENTER
const ZOOM = 14;                       // CorridorMap's DEFAULT_ZOOM

async function api(base: string | undefined, path: string, init?: { method?: string; body?: unknown }) {
  const res = await fetch(new URL(`/api${path}`, base), {
    method: init?.method ?? 'GET',
    headers: init?.body ? { 'content-type': 'application/json' } : undefined,
    body: init?.body ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) throw new Error(`${init?.method ?? 'GET'} ${path}: HTTP ${res.status} ${await res.text()}`);
  return res.json();
}
const newStudy = (base: string | undefined, name: string) =>
  api(base, '/studies', { method: 'POST', body: { name, mode: 'profile', from_year: 2021, to_year: 2025 } });
async function studyWithCorridor(base: string | undefined, name: string) {
  const s = await newStudy(base, name);
  await api(base, `/studies/${s.id}/corridor`, { method: 'PUT', body: { line: LINE } });
  return s.id as string;
}
const fmt = (n: number) => n.toLocaleString('en-US');

// Web Mercator, the map's own projection: a lat/lon's pixel offset from the map's center at a zoom level.
const mx = (lon: number) => (lon + 180) / 360;
const my = (lat: number) => (1 - Math.log(Math.tan((lat * Math.PI) / 180) + 1 / Math.cos((lat * Math.PI) / 180)) / Math.PI) / 2;
function toPixel(box: { x: number; y: number; width: number; height: number }, [lat, lon]: number[]) {
  const s = 256 * 2 ** ZOOM;
  return { x: box.x + box.width / 2 + (mx(lon) - mx(CENTER[1])) * s, y: box.y + box.height / 2 + (my(lat) - my(CENTER[0])) * s };
}

test.beforeEach(async ({ app, browser }) => {
  const own = new URL(app.baseUrl!).host;
  await browser.route('**/*', (route) => (new URL(route.request.url).host === own ? route.continue() : route.abort()));
});

test('Corridor: drawing the line on the map finds the same corridor as the API', async ({ app, screen, browser }) => {
  const s = await newStudy(app.baseUrl, 'Screen test: draw');
  await app.open(`/s/${s.id}/corridor`);
  await expect(screen.getByRole('status')).toContainText('Click on the street where the study starts (A)');
  const box = (await browser.locator('.ciq-map').boundingBox())!;
  const pts = LINE.map((p) => toPixel(box, p));
  for (const p of pts) await screen.tapAt(p);
  await expect(screen.getByText(`${LINE.length} points drawn`)).toBeVisible();
  // a double-click on the last point finishes the line (two quick presses)
  const last = pts[pts.length - 1];
  await browser.mouse.move(last.x, last.y);
  await browser.mouse.down(); await browser.mouse.up(); await browser.mouse.down(); await browser.mouse.up();
  await expect(screen.getByRole('button', 'Find intersections →')).toBeEnabled();
  await screen.getByRole('button', 'Find intersections →').tap();
  await expect.poll(async () => Boolean((await api(app.baseUrl, `/studies/${s.id}/network`)).line),
    { timeout: 20000 }).toBe(true);
  const n = await api(app.baseUrl, `/studies/${s.id}/network`);
  await expect(screen.getByRole('heading', n.corridor_name)).toBeVisible();
  for (const it of n.intersections) {
    await expect(screen.getByRole('checkbox', `Study intersection: ${it.name}`)).toBeVisible();
  }
  // the drawn line lands on the recorded corridor: every drawn point within ~30 m (map pixel rounding)
  for (const [lat, lon] of LINE) {
    const d = Math.min(...n.line.map(([a, b]: number[]) => Math.hypot((a - lat) * 111000, (b - lon) * 92000)));
    expect(d).toBeLessThan(30);
  }
});

for (const width of [375, 768]) {
  test(`At ${width}px: setup, corridor and profile fit the screen with the key numbers visible`, async ({ app, screen, browser }) => {
    await browser.setViewport({ width, height: width === 375 ? 812 : 1024 });
    const id = await studyWithCorridor(app.baseUrl, `Screen test: ${width}px`);
    const noSideways = async () => browser.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);

    await app.open('/');
    await expect(screen.getByRole('button', 'Draw the corridor →')).toBeVisible();
    expect(await noSideways()).toBe(true);

    await app.open(`/s/${id}/corridor`);
    await expect(screen.getByRole('button', 'Build the profile →')).toBeVisible();
    expect(await noSideways()).toBe(true);

    await app.open(`/s/${id}/profile`);
    const kpis = browser.locator('[aria-label="Key numbers"]');
    await expect(kpis).toBeVisible({ timeout: 60000 });
    expect(await noSideways()).toBe(true);
    const kb = (await kpis.boundingBox())!;
    expect(kb.x).toBeGreaterThanOrEqual(0);
    expect(kb.x + kb.width).toBeLessThanOrEqual(width + 1);
    // every key-number tile is on screen horizontally and doesn't overlap the next one
    const tiles = await browser.evaluate(() => [...document.querySelectorAll('[aria-label="Key numbers"] .sf-kpi')]
      .map((el) => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }));
    for (let i = 0; i < tiles.length; i++) {
      for (let j = i + 1; j < tiles.length; j++) {
        const [a, b] = [tiles[i], tiles[j]];
        const overlap = a[0] < b[2] - 1 && b[0] < a[2] - 1 && a[1] < b[3] - 1 && b[1] < a[3] - 1;
        expect(overlap).toBe(false);
      }
      expect(tiles[i][0]).toBeGreaterThanOrEqual(0);
      expect(tiles[i][2]).toBeLessThanOrEqual(width + 1);
    }
  });
}

test('Crash profile: the road-user section matches the data', async ({ app, browser }) => {
  const id = await studyWithCorridor(app.baseUrl, 'Screen test: road users');
  await app.open(`/s/${id}/profile`);
  await expect(browser.locator('[aria-label="Pedestrians and bicyclists"]')).toBeVisible({ timeout: 60000 });
  const p = await api(app.baseUrl, `/studies/${id}/profile`);
  const t19 = Object.fromEntries(p.tables.find((t: any) => t.id === 'T19').rows.map((r: any) => [r.key, r.values]));
  for (const k of ['ped', 'bike', 'ebike', 'escooter', 'motorcycle']) {
    const shown = await browser.evaluate((key: string) => {
      const li = document.querySelector(`[data-testid="vru-${key}"]`);
      return li ? [li.querySelector('.n')?.textContent?.trim(), li.querySelector('.ksi')?.textContent?.trim()] : null;
    }, k);
    expect(shown, k).toEqual([fmt(t19[k]?.crashes ?? 0), `${fmt(t19[k]?.ksi_crashes ?? 0)} KSI`]);
  }
  // the "how dangerous" bars: each group's KSI share and counts
  const bars = await browser.evaluate(() => [...document.querySelectorAll('[data-testid^="danger-"]')]
    .map((el) => [el.getAttribute('data-testid')!.slice(7), el.querySelector('.v')?.textContent?.trim(),
                  el.querySelector('.nn')?.textContent?.trim()]));
  for (const [k, pct, nn] of bars) {
    const v = t19[k as string];
    expect(pct, k).toBe(`${fmt(v.ksi_pct)}%`);
    expect(nn, k).toBe(`${fmt(v.ksi_crashes)} of ${fmt(v.crashes)}`);
  }
});
