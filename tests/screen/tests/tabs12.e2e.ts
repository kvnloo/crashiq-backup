// Tester screen tests: CrashIQ tabs 1-2 (Setup, Corridor, Crash profile and its review list).
// Exact steps only: no agent steps, no model. Every number the screen shows is checked against the app's own API
// for the same study, so a test fails when the screen and the data disagree.
import { expect } from 'e2e';
import { test } from '@e2e-dev/web';

// The recorded Crenshaw Boulevard corridor (tests/fixtures), the same line the backend tests use.
const LINE = [[33.8953, -118.32662], [33.9040, -118.32662], [33.9123, -118.32662]];

async function api(base: string | undefined, path: string, init?: { method?: string; body?: unknown }) {
  const res = await fetch(new URL(`/api${path}`, base), {
    method: init?.method ?? 'GET',
    headers: init?.body ? { 'content-type': 'application/json' } : undefined,
    body: init?.body ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) throw new Error(`${init?.method ?? 'GET'} ${path}: HTTP ${res.status} ${await res.text()}`);
  return res.json();
}

async function studyWithCorridor(base: string | undefined, name: string) {
  const s = await api(base, '/studies', { method: 'POST', body: { name, mode: 'profile', from_year: 2021, to_year: 2025 } });
  const net = await api(base, `/studies/${s.id}/corridor`, { method: 'PUT', body: { line: LINE } });
  return { id: s.id as string, net };
}

const t1 = (profile: any) =>
  Object.fromEntries(profile.tables.find((t: any) => t.id === 'T1').rows.map((r: any) => [r.key, r.values.value]));
const fmt = (n: number) => n.toLocaleString('en-US');

// The map loads tiles from the internet; the tests keep to the app itself.
test.beforeEach(async ({ app, browser }) => {
  const own = new URL(app.baseUrl!).host;
  await browser.route('**/*', (route) => (new URL(route.request.url).host === own ? route.continue() : route.abort()));
});

test('Setup: a project name is required before drawing', async ({ app, screen }) => {
  await app.open('/');
  await expect(screen.getByRole('heading', 'Where are crashes concentrating on this corridor?')).toBeVisible();
  await expect(screen.getByRole('button', 'Draw the corridor →')).toBeDisabled();
  await screen.getByLabel('Project').fill('Screen test: Setup');
  await expect(screen.getByRole('button', 'Draw the corridor →')).toBeEnabled();
});

test('Setup: creating a study opens the corridor step ready to draw', async ({ app, screen, browser }) => {
  await app.open('/');
  await screen.getByLabel('Project').fill('Screen test: new study');
  await screen.getByLabel('Crash history').selectOption({ value: '5' });
  await screen.getByRole('button', 'Draw the corridor →').tap();
  await expect(browser).toHaveURL(/\/s\/[^/]+\/corridor$/);
  await expect(screen.getByRole('heading', 'Draw the corridor')).toBeVisible();
  await expect(screen.getByRole('status')).toContainText('Click on the street where the study starts (A)');
  const id = new URL(await browser.url()).pathname.split('/')[2];
  const s = await api(app.baseUrl, `/studies/${id}`);
  expect(s.name).toBe('Screen test: new study');
  expect(s.to_year - s.from_year + 1).toBe(5);
});

test('Corridor: the screen lists every location the app detected', async ({ app, screen }) => {
  const { id, net } = await studyWithCorridor(app.baseUrl, 'Screen test: corridor list');
  await app.open(`/s/${id}/corridor`);
  const panel = screen.getByRole('complementary', 'Corridor locations');
  await expect(panel.getByRole('heading', net.corridor_name)).toBeVisible();
  for (const it of net.intersections) {
    await expect(panel.getByRole('checkbox', `Study intersection: ${it.name}`)).toBeVisible();
    expect(await panel.getByRole('checkbox', `Study intersection: ${it.name}`).isChecked()).toBe(it.is_study);
  }
  await expect(screen.getByRole('button', 'Build the profile →')).toBeEnabled();
});

test('Corridor: unticking a study intersection is saved', async ({ app, screen }) => {
  const { id, net } = await studyWithCorridor(app.baseUrl, 'Screen test: untick');
  const target = net.intersections.find((i: any) => i.is_study);
  await app.open(`/s/${id}/corridor`);
  await screen.getByRole('checkbox', `Study intersection: ${target.name}`).uncheck();
  await expect.poll(async () => (await api(app.baseUrl, `/studies/${id}/network`))
    .intersections.find((i: any) => i.id === target.id).is_study).toBe(false);
});

test('Crash profile: the key numbers match the data', async ({ app, browser }) => {
  const { id } = await studyWithCorridor(app.baseUrl, 'Screen test: key numbers');
  await app.open(`/s/${id}/profile`);
  await expect(browser.locator('[aria-label="Key numbers"]')).toBeVisible({ timeout: 60000 });
  const v = t1(await api(app.baseUrl, `/studies/${id}/profile`));
  // Each tile's own number (its first text), without the small unit after it.
  const tiles = await browser.evaluate(() => [...document.querySelectorAll('[aria-label="Key numbers"] .sf-kpi')]
    .map((k) => [k.querySelector('.sf-kpi__label')?.firstChild?.textContent?.trim(),
                 k.querySelector('.sf-kpi__value')?.firstChild?.textContent?.trim()]));
  expect(tiles).toEqual([
    ['Crashes', fmt(v.crashes)],
    ['KSI', fmt(v.ksi_crashes)],
    ['Injury crashes', fmt(v.injury_crashes)],
    ['Per mile · year', fmt(v.crashes_per_mi_yr)],
  ]);
});

test('Crash profile: the data-quality line matches the counts', async ({ app, screen }) => {
  const { id } = await studyWithCorridor(app.baseUrl, 'Screen test: quality');
  await app.open(`/s/${id}/profile`);
  const q = screen.getByRole('region', 'Data quality');
  await expect(q).toBeVisible({ timeout: 60000 });
  const v = t1(await api(app.baseUrl, `/studies/${id}/profile`));
  // 'Crashes' counts placed crashes; the ones still to review are shown beside them, not inside.
  expect(v.located_gps + v.located_exact + v.located_other + v.user_placed).toBe(v.crashes);
  await expect(q).toContainText(`${fmt(v.located_gps)} GPS`);
  await expect(q).toContainText(`${fmt(v.unplaced)} to review`);
});

test('Review list: placing a crash takes it off the list and into the counts', async ({ app, screen }) => {
  const { id } = await studyWithCorridor(app.baseUrl, 'Screen test: review');
  await app.open(`/s/${id}/profile`);
  await expect(screen.getByRole('region', 'Data quality')).toBeVisible({ timeout: 60000 });
  const before = t1(await api(app.baseUrl, `/studies/${id}/profile`));
  expect(before.unplaced).toBeGreaterThan(0);                 // the screen-test fixture leaves 3 for review
  await screen.getByRole('button', new RegExp(`^${before.unplaced} to review`)).tap();
  await expect(screen.getByRole('heading', 'Review list')).toBeVisible();
  const review = await api(app.baseUrl, `/studies/${id}/review`);
  const group = review.groups[0];
  await screen.getByRole('button', { name: new RegExp(group.label ?? group.key), expanded: false }).first().tap();
  await screen.getByRole('button', 'At an intersection').first().tap();
  const target = review.intersections[0];
  await screen.getByRole('combobox', /^Intersection for /).first().selectOption({ label: target.name });
  await screen.getByRole('button', /^Place/).first().tap();
  await expect.poll(async () => t1(await api(app.baseUrl, `/studies/${id}/profile`)).user_placed).toBeGreaterThan(0);
  const after = t1(await api(app.baseUrl, `/studies/${id}/profile`));
  expect(after.unplaced + after.user_placed).toBe(before.unplaced + before.user_placed);
  await screen.getByRole('button', '← Crash profile').tap();
  const q = screen.getByRole('region', 'Data quality');
  await expect(q).toContainText(`${fmt(after.user_placed)} by you`);
  if (after.unplaced) await expect(q).toContainText(`${fmt(after.unplaced)} to review`);
  else await expect(q).not.toContainText('to review');
});
