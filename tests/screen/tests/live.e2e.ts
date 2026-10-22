// Tester screen tests on the LIVE Crenshaw recording (#177, PM follow-up): the review list's place, exclude and
// undo flow on real CCRS rows. Run with `npm run test:live` (e2e.live.config.ts). Exact steps only, no model.
import { expect } from 'e2e';
import { test } from '@e2e-dev/web';

const LINE = [[33.8953, -118.32662], [33.904, -118.32662], [33.9123, -118.32662]];   // tests/fixtures/live

async function api(base: string | undefined, path: string, init?: { method?: string; body?: unknown }) {
  const res = await fetch(new URL(`/api${path}`, base), {
    method: init?.method ?? 'GET',
    headers: init?.body ? { 'content-type': 'application/json' } : undefined,
    body: init?.body ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) throw new Error(`${init?.method ?? 'GET'} ${path}: HTTP ${res.status} ${await res.text()}`);
  return res.json();
}
const t1 = (p: any) => Object.fromEntries(p.tables.find((t: any) => t.id === 'T1').rows.map((r: any) => [r.key, r.values.value]));
const fmt = (n: number) => n.toLocaleString('en-US');

test.beforeEach(async ({ app, browser }) => {
  const own = new URL(app.baseUrl!).host;
  await browser.route('**/*', (route) => (new URL(route.request.url).host === own ? route.continue() : route.abort()));
});

async function openReview(app: any, screen: any, name: string) {
  const s = await api(app.baseUrl, '/studies', { method: 'POST', body: { name, mode: 'profile', from_year: 2021, to_year: 2025 } });
  await api(app.baseUrl, `/studies/${s.id}/corridor`, { method: 'PUT', body: { line: LINE } });
  await app.open(`/s/${s.id}/profile`);
  await expect(screen.getByRole('region', 'Data quality')).toBeVisible({ timeout: 90000 });
  const before = t1(await api(app.baseUrl, `/studies/${s.id}/profile`));
  const review = await api(app.baseUrl, `/studies/${s.id}/review`);
  return { id: s.id as string, before, review };
}

// Which crashes a review form acts on, from its own label: "crash <id>" or "all <n> crashes at <group key>".
function idsFor(label: string, review: any): string[] {
  const one = label.match(/crash (\S+)$/);
  if (one && !label.includes(' crashes at ')) return [one[1]];
  const key = label.replace(/^.* crashes at /, '');
  return review.groups.find((g: any) => g.key === key).crashes.map((c: any) => String(c.crash_id));
}

test('Live: excluding a crash with a reason, then undo, restores the review list and the counts', async ({ app, screen }) => {
  const { id, before, review } = await openReview(app, screen, 'Live screen test: exclude + undo');
  expect(review.open).toBeGreaterThan(0);
  await screen.getByRole('button', new RegExp(`^${fmt(before.unplaced)} to review`)).tap();
  await expect(screen.getByRole('heading', 'Review list')).toBeVisible();
  // the first Exclude on the list opens its form; the form's label says which crash (or group) it is for
  await screen.getByRole('button', 'Exclude').first().tap();
  const input = screen.getByRole('textbox', /^Why exclude /);
  const label = (await input.getAttribute('aria-label'))!;
  const ids = idsFor(label, review);
  await input.fill('Screen test: parking lot, not the road');
  await input.press('Enter');
  await expect.poll(async () => (await api(app.baseUrl, `/studies/${id}/review`)).open).toBe(review.open - ids.length);
  const after = await api(app.baseUrl, `/studies/${id}/review`);
  for (const cid of ids) {
    const d = after.decided.find((x: any) => String(x.crash_id) === cid);
    expect(d?.decision, cid).toMatchObject({ action: 'exclude', reason: 'Screen test: parking lot, not the road' });
  }
  await expect(screen.getByText('excluded: Screen test: parking lot, not the road').first()).toBeVisible();
  // undo puts it back
  await screen.getByRole('button', 'Undo last').tap();
  await expect.poll(async () => (await api(app.baseUrl, `/studies/${id}/review`)).open).toBe(review.open);
  const undone = await api(app.baseUrl, `/studies/${id}/review`);
  for (const cid of ids) expect(undone.decided.find((x: any) => String(x.crash_id) === cid), cid).toBeUndefined();
  expect(t1(await api(app.baseUrl, `/studies/${id}/profile`))).toMatchObject({ unplaced: before.unplaced, crashes: before.crashes });
  await expect(screen.getByRole('button', 'Undo last')).toBeDisabled();
});

test('Live: placing a crash at an intersection counts it there; undo takes it back out', async ({ app, screen }) => {
  const { id, before, review } = await openReview(app, screen, 'Live screen test: place + undo');
  await screen.getByRole('button', new RegExp(`^${fmt(before.unplaced)} to review`)).tap();
  await screen.getByRole('button', 'At an intersection').first().tap();
  const pickBox = screen.getByRole('combobox', /^Intersection for /);
  const ids = idsFor((await pickBox.getAttribute('aria-label'))!, review);
  const target = review.intersections[0];
  await pickBox.selectOption({ label: target.name });
  await screen.getByRole('button', /^Place( \d+)?$/).tap();
  await expect.poll(async () => t1(await api(app.baseUrl, `/studies/${id}/profile`)).user_placed).toBe(before.user_placed + ids.length);
  const mid = t1(await api(app.baseUrl, `/studies/${id}/profile`));
  expect(mid.unplaced).toBe(before.unplaced - ids.length);
  expect(mid.crashes).toBe(before.crashes + ids.length);              // a placed crash now counts for the corridor
  const loc = await api(app.baseUrl, `/studies/${id}/profile/locations/${encodeURIComponent(target.id)}`);
  for (const cid of ids) expect(loc.crashes.map((c: any) => String(c.crash_id)), cid).toContain(cid);
  await screen.getByRole('button', 'Undo last').tap();
  await expect.poll(async () => t1(await api(app.baseUrl, `/studies/${id}/profile`)).user_placed).toBe(before.user_placed);
  expect(t1(await api(app.baseUrl, `/studies/${id}/profile`))).toMatchObject({ unplaced: before.unplaced, crashes: before.crashes });
});
