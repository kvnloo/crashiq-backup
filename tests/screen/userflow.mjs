// Hermes end-to-end check of the user flow on the container (live data): draw a corridor on the map, build the
// profile, open findings, export PDF + XLSX. Plus two more corridors set through the same API the map calls.
// Run: APP_PASSWORD=... node userflow.mjs   (container on :8001). Screenshots + JSON report in OUT.
import { chromium } from 'playwright-core';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';

const BASE = process.env.CRASHIQ_URL || 'http://127.0.0.1:8001';
const OUT = process.env.OUT || `${process.env.HOME}/.hermes/cache/scratch/userflow`;
mkdirSync(OUT, { recursive: true });
const PW = process.env.APP_PASSWORD;
const AUTH = 'Basic ' + Buffer.from(`u:${PW}`).toString('base64');
const report = { steps: [], console: [], failed: [] };
const step = (name, ok, extra = {}) => { report.steps.push({ name, ok, ...extra }); console.log(ok ? 'OK  ' : 'FAIL', name, JSON.stringify(extra)); };

async function api(path, init = {}) {
  const r = await fetch(BASE + '/api' + path, { method: init.method || 'GET', headers: { authorization: AUTH, 'content-type': 'application/json' },
    body: init.body ? JSON.stringify(init.body) : undefined });
  const t = await r.text(); let j; try { j = JSON.parse(t); } catch { j = t; }
  return { status: r.status, body: j };
}

const CENTER = [33.9038, -118.3266], ZOOM = 14;
const mx = (lon) => (lon + 180) / 360;
const my = (lat) => (1 - Math.log(Math.tan((lat * Math.PI) / 180) + 1 / Math.cos((lat * Math.PI) / 180)) / Math.PI) / 2;
const toPixel = (box, [lat, lon]) => { const s = 256 * 2 ** ZOOM;
  return { x: box.x + box.width / 2 + (mx(lon) - mx(CENTER[1])) * s, y: box.y + box.height / 2 + (my(lat) - my(CENTER[0])) * s }; };

const browser = await chromium.launch();
const ctx = await browser.newContext({ httpCredentials: { username: 'u', password: PW }, acceptDownloads: true, viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
page.on('console', (m) => { if (m.type() === 'error') report.console.push(m.text().slice(0, 300)); });
page.on('pageerror', (e) => report.console.push('pageerror: ' + String(e).slice(0, 300)));
page.on('requestfailed', (r) => report.failed.push(`${r.url().slice(0, 120)} ${r.failure()?.errorText}`));
page.on('response', (r) => { if (r.status() >= 400 && r.url().startsWith(BASE)) report.failed.push(`${r.status()} ${r.url().slice(0, 120)}`); });
const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` });

async function profileAndExport(id, tag) {
  await page.goto(`${BASE}/s/${id}/profile`);
  const t0 = Date.now();
  await page.getByRole('button', { name: 'See findings →' }).waitFor({ timeout: 900000 });
  step(`${tag}: crash profile built`, true, { seconds: Math.round((Date.now() - t0) / 1000) });
  await shot(`${tag}-3-profile`);
  const prof = (await api(`/studies/${id}/profile`)).body;
  const t1 = prof.tables.find((t) => t.id === 'T1');
  step(`${tag}: profile numbers`, true, { T1: Object.fromEntries(t1.rows.map((r) => [r.key, r.values.value])), caveats: prof.caveats.length });
  await page.getByRole('button', { name: 'See findings →' }).click();
  await page.waitForURL(/\/findings$/);
  await page.waitForTimeout(4000);
  await shot(`${tag}-4-findings`);
  const f = (await api(`/studies/${id}/findings`)).body;
  step(`${tag}: findings`, true, { count: (f.findings || f).length });
  await page.goto(`${BASE}/s/${id}/export`);
  const btn = page.getByRole('button', { name: /Export 2 files/ });
  await btn.waitFor(); await page.waitForFunction(() => !document.querySelector('.cta-bar button')?.disabled, null, { timeout: 120000 });
  await shot(`${tag}-5-export`);
  const downloads = [];
  page.on('download', (d) => downloads.push(d));
  await btn.click();
  for (let i = 0; i < 120 && downloads.length < 2; i++) await page.waitForTimeout(500);
  const files = [];
  for (const d of downloads) {
    const p = `${OUT}/${tag}-${d.suggestedFilename()}`; await d.saveAs(p);
    const head = readFileSync(p).subarray(0, 4).toString('latin1');
    files.push({ name: d.suggestedFilename(), bytes: readFileSync(p).length, head });
  }
  const ok = files.length === 2 && files.some((x) => x.head.startsWith('%PDF')) && files.some((x) => x.head.startsWith('PK'));
  step(`${tag}: export PDF + XLSX downloaded`, ok, { files });
}

try {
  // 1) Setup in the UI
  await page.goto(BASE + '/');
  await page.getByLabel('Project').fill('Hermes check: Crenshaw Blvd');
  await page.getByLabel('Crash history').selectOption({ value: '5' });
  await page.getByRole('button', { name: 'Draw the corridor →' }).click();
  await page.waitForURL(/\/s\/[^/]+\/corridor$/);
  const id = new URL(page.url()).pathname.split('/')[2];
  step('Crenshaw: study created in Setup', true, { id });
  // 2) Draw the line on the map
  await page.locator('.ciq-map').waitFor();
  await page.waitForTimeout(3000);
  await shot('crenshaw-1-map');
  const box = await page.locator('.ciq-map').boundingBox();
  const LINE = [[33.8953, -118.32662], [33.9040, -118.32662], [33.9123, -118.32662]];
  const pts = LINE.map((p) => toPixel(box, p));
  for (const p of pts) { await page.mouse.click(p.x, p.y); await page.waitForTimeout(400); }
  const last = pts[pts.length - 1];
  await page.mouse.dblclick(last.x, last.y);
  const find = page.getByRole('button', { name: 'Find intersections →' });
  await find.waitFor(); 
  const t0 = Date.now();
  await find.click();
  await page.getByRole('button', { name: 'Build the profile →' }).waitFor({ timeout: 600000 });
  const net = (await api(`/studies/${id}/network`)).body;
  step('Crenshaw: corridor drawn on the map, intersections found', (net.intersections || []).length > 0,
    { seconds: Math.round((Date.now() - t0) / 1000), corridor: net.corridor_name, intersections: (net.intersections || []).length, segments: (net.segments || []).length });
  await shot('crenshaw-2-corridor');
  await profileAndExport(id, 'crenshaw');

  // 3) Two more corridor types through the same corridor API the map uses
  // CORRIDORS='[[tag,name,[[lat,lon],...]],...]' replaces the default extra corridors
  for (const [tag, name, line] of process.env.CORRIDORS ? JSON.parse(process.env.CORRIDORS) : [
    ['capistrano', 'Hermes check: Camino Capistrano, San Juan Capistrano', [[33.485658, -117.666903], [33.490503, -117.664085], [33.49551, -117.662593], [33.499891, -117.6625]]],
    ['sherman', 'Hermes check: Sherman Way, LA', [[34.20123, -118.50921], [34.201233, -118.491896]]],
  ]) {
    const s = (await api('/studies', { method: 'POST', body: { name, mode: 'profile' } })).body;
    const t = Date.now();
    const c = await api(`/studies/${s.id}/corridor`, { method: 'PUT', body: { line } });
    step(`${tag}: corridor`, c.status === 200, { status: c.status, seconds: Math.round((Date.now() - t) / 1000),
      detail: c.status === 200 ? undefined : c.body, intersections: c.body?.intersections?.length });
    if (c.status === 200) await profileAndExport(s.id, tag);
  }
} catch (e) {
  step('run', false, { error: String(e).slice(0, 500) });
  await shot('zz-error');
} finally {
  writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 1));
  console.log('console errors:', report.console.length, 'failed requests:', report.failed.length);
  await browser.close();
}
