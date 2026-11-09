import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { META, mockApi, renderAt } from '../test-utils'
import network from '../__fixtures__/network.json'
import pull from '../__fixtures__/pull.json'
import profile from '../__fixtures__/profile.json'
import crashes from '../__fixtures__/crashes.json'
import location from '../__fixtures__/location.json'
import assignment from '../__fixtures__/assignment.json'
import { cell, table } from '../lib/tables'

vi.mock('../components/ProfileMap', () => ({ default: (p) => <div data-testid="map" data-n={p.crashes.length} /> }))

const STUDY = { id: 's1', name: 'Crenshaw', mode: 'tis', from_year: 2021, to_year: 2025, radius_ft: 250, buffer_ft: 100 }
const routes = {
  'GET /studies/meta': META, 'GET /studies/:id': STUDY, 'GET /studies/:id/network': network,
  'POST /studies/:id/crashes/pull': pull, 'GET /studies/:id/profile': profile, 'GET /studies/:id/crashes': crashes, 'GET /studies/:id/assignment': assignment,
  'GET /studies/:id/profile/locations/:lid': location,
}
const nf = new Intl.NumberFormat('en-US')

describe('Crash profile screen', () => {
  it('shows Crashes, KSI, Fatal (only when there is one) and per mile·year, each equal to its T1 cell (#269)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    const kpis = await screen.findByLabelText('Key numbers')
    const values = within(kpis).getAllByText((_, el) => el.classList?.contains('sf-kpi__value'))
    const keys = ['crashes', 'ksi_crashes', ...(cell(profile, 'T1/fatal_crashes/value') ? ['fatal_crashes'] : []), 'crashes_per_mi_yr']
    expect(values).toHaveLength(keys.length)
    values.forEach((el, i) => expect(el.textContent.startsWith(nf.format(cell(profile, `T1/${keys[i]}/value`)))).toBe(true))
    expect(within(kpis).queryByText(/Injury crashes/)).toBeNull()
  })

  it('a source with no injury levels says KSI is fatal only (#19)', async () => {
    const note = 'NYPD reports injured or killed only: KSI = fatal only, and there is no A/B/C split.'
    mockApi({ ...routes, 'GET /studies/:id/profile': { ...profile, state: 'NY', severity_note: note, source_short: 'NYC Open Data' } })
    renderAt('/s/s1/profile')
    const kpis = await screen.findByLabelText('Key numbers')
    expect(within(kpis).getByText('fatal only: no injury levels')).toBeInTheDocument()
    expect(screen.getByText(/crashes killed someone \(KSI = fatal only\)/)).toHaveTextContent(note)
    expect(screen.queryByText(/killed or seriously injured/)).toBeNull()
  })

  it('a fatal crash gets its own KPI; none, no Fatal box (#269)', async () => {
    const t1 = (n) => ({ ...profile, tables: profile.tables.map((t) => (t.id !== 'T1' ? t : { ...t, rows: t.rows.map((r) => (
      r.key === 'fatal_crashes' ? { ...r, values: { ...r.values, value: n } } : r)) })) })
    mockApi({ ...routes, 'GET /studies/:id/profile': t1(2) })
    renderAt('/s/s1/profile')
    const kpis = await screen.findByLabelText('Key numbers')
    expect(within(kpis).getByText(/^Fatal/)).toBeInTheDocument()
  })

  it('tab 3 order: summary first, then ped/bike, where, pattern, how bad, why, trend, when (#269)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const want = ['Key numbers', 'Data quality', 'Location ranking', 'Pedestrians and bicyclists', 'Crashes along the corridor',
      'Collision type by location', 'Severity', 'Why did they crash?', 'Crashes by year', 'When crashes happen']
    // "Why did they crash?" needs T18, which this fixture lacks: checked in order when present
    const els = want.map((l) => (l === 'Why did they crash?' ? screen.queryByLabelText(l) : screen.getByLabelText(l))).filter(Boolean)
    for (let i = 1; i < els.length; i++) {
      expect(els[i - 1].compareDocumentPosition(els[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    }
    expect(screen.queryByRole('heading', { name: 'Collision type' })).toBeNull()        // the grid carries those counts
  })

  it('when crashes happen: 24 hour bars from T26 and 7 day bars from T27; the hour × day grid folded (#269)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    const sec = await screen.findByLabelText('When crashes happen')
    const hours = within(within(sec).getByLabelText('Crashes by hour of day')).getAllByTestId('colbar')
    expect(hours).toHaveLength(24)
    table(profile, 'T26').rows.forEach((r, i) => expect(hours[i]).toHaveAttribute('aria-label', `${r.label}, ${r.values.crashes}`))
    const days = within(within(sec).getByLabelText('Crashes by day of week')).getAllByTestId('colbar')
    table(profile, 'T27').rows.forEach((r, i) => expect(days[i]).toHaveAttribute('aria-label', `${r.label}, ${r.values.crashes}`))
    expect(within(sec).getByText('Show hour × day grid').closest('details').open).toBe(false)
  })

  it('renders the location table straight from T2 and collision bars from T4', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const t2 = table(profile, 'T2')
    const full = screen.getByLabelText('Location ranking').querySelector('details')       // the full T2 table (#103)
    const rows = within(full).getAllByRole('row').filter((r) => within(r).queryByRole('button'))
    expect(rows).toHaveLength(t2.rows.length)
    t2.rows.forEach((r, i) => {
      const cells = within(rows[i]).getAllByRole('cell').map((c) => c.textContent)
      expect(cells[0]).toContain(r.label)
      expect(cells.slice(1, 6)).toEqual(['crashes', 'ksi_crashes', 'injury_crashes', 'dark_crashes', 'crashes_per_year']
        .map((k) => nf.format(r.values[k])))
    })
    // #269: the collision-type totals are the grid's total row, from T4
    const tot = within(screen.getByTestId('grid-total')).getAllByRole('cell')
    const t4 = table(profile, 'T4')
    tot.forEach((c) => expect(t4.rows.some((r) => r.label === c.getAttribute('title') && nf.format(r.values.crashes) === c.textContent)).toBe(true))
  })

  it('cites tables with a small ⓘ, not visible text', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    expect(screen.queryByText(/table T\d/i)).toBeNull()
    expect(screen.getAllByLabelText(/Source: table T/).length).toBeGreaterThan(4)
  })

  it('shows caveats only when they apply, and the provenance one click away', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const cav = screen.getByLabelText('Caveats')
    expect(within(cav).getAllByRole('listitem')).toHaveLength(profile.caveats.length)
    expect(within(cav).queryByText(/COVID/)).toBeNull()                  // this fixture's caveats carry no COVID note
    const details = screen.getByText('Where these crashes come from').closest('details')
    expect(details.open).toBe(false)
    expect(details.contains(cav)).toBe(true)                 // #269: at the bottom, in "Where these crashes come from"
    expect(within(details).getByText('Not placed yet (no coordinates)')).toBeInTheDocument()
  })

  it('drills into a location', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const first = table(profile, 'T2').rows[0]
    fireEvent.click(within(screen.getByLabelText('Location ranking')).getAllByRole('button', { name: first.label })[0])
    await screen.findByText('← All locations')
    expect(screen.getAllByRole('row').length).toBeGreaterThanOrEqual(location.crashes.length)
    fireEvent.click(screen.getByText('← All locations'))
    await waitFor(() => expect(screen.getByLabelText('Key numbers')).toBeInTheDocument())
  })

  it('has one primary: See findings', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    expect(document.querySelectorAll('.sf-btn--go')).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'See findings →' })).toBeInTheDocument()
  })

  it('shows each rate against its critical rate, red when over', async () => {
    const prof = JSON.parse(JSON.stringify(profile))
    const t2 = prof.tables.find((x) => x.id === 'T2')
    const ints = t2.rows.filter((r) => r.values.kind === 'intersection')
    ints.forEach((r, i) => Object.assign(r.values, { rate: 1 + i * 0.2, rate_unit: 'per MEV', critical_rate: 1.5,
      reference_rate: 1.2, over_critical: 1 + i * 0.2 > 1.5 ? 'Yes' : 'No' }))
    mockApi({ ...routes, 'GET /studies/:id/profile': prof })
    renderAt('/s/s1/profile')
    expect(await screen.findByText('Rate vs critical')).toBeInTheDocument()
    const over = ints.filter((r) => r.values.over_critical === 'Yes').length
    expect(document.querySelectorAll('.rbar i.over')).toHaveLength(over)
    expect(document.querySelectorAll('.rbar b')).toHaveLength(ints.length)
  })

  it('shows the background pull step, then the profile when it is done (#54)', async () => {
    let polls = 0
    mockApi({
      ...routes,
      'POST /studies/:id/crashes/pull': { job: { state: 'running', step: 'Starting', done: 0, total: 0 } },
      'GET /studies/:id/crashes/pull/status': () => (++polls < 2
        ? { state: 'running', step: 'Crash reports 2023', done: 2, total: 5 }
        : { state: 'done', step: 'Done', summary: pull }),
    })
    renderAt('/s/s1/profile')
    expect(await screen.findByText('Crash reports 2023 · 3 of 5', {}, { timeout: 3000 })).toBeInTheDocument()
    expect(await screen.findByLabelText('Key numbers', {}, { timeout: 4000 })).toBeInTheDocument()
  })

  it('says why when the background pull fails', async () => {
    mockApi({
      ...routes,
      'POST /studies/:id/crashes/pull': { job: { state: 'running', step: 'Starting', done: 0, total: 0 } },
      'GET /studies/:id/crashes/pull/status': { state: 'error', status: 502, error: 'data.ca.gov is down' },
    })
    renderAt('/s/s1/profile')
    expect(await screen.findByRole('alert', {}, { timeout: 3000 })).toHaveTextContent('data.ca.gov is down')
  })

  it('opens the review list, excludes a group with a reason, and refreshes the profile (#97)', async () => {
    const REVIEW = {
      open: 2, can_undo: false, decided: [],
      intersections: [{ id: 'osm-1', name: 'Marine Avenue', lat: 33.8953, lon: -118.3266 }],
      groups: [{ key: 'CRENSHAW BLVD / NOT STATED', primary: 'CRENSHAW BLVD', secondary: 'NOT STATED', count: 2,
        reasons: { no_cross_street: 2 }, with_suggestion: 0,
        crashes: [{ crash_id: '1', date: '2023-01-02', hour: 8, severity: 'C', collision_type: 'REAR END', primary_road: 'CRENSHAW BL', secondary_road: 'NOT STATED', reason: 'no_cross_street' },
          { crash_id: '2', date: '2024-03-04', hour: 17, severity: 'O', collision_type: 'BROADSIDE', primary_road: 'CRENSHAW BL', secondary_road: 'NOT STATED', reason: 'no_cross_street' }] }],
    }
    const AFTER = { ...REVIEW, open: 0, can_undo: true, groups: [],
      decided: [{ crash_id: '1', primary_road: 'CRENSHAW BL', secondary_road: 'NOT STATED', decision: { action: 'exclude', reason: 'Parking lot' } }] }
    const calls = mockApi({ ...routes, 'GET /studies/:id/review': REVIEW,
      'POST /studies/:id/review/decisions': () => ({ decided: 2, review: AFTER }) })
    renderAt('/s/s1/profile')
    fireEvent.click(await screen.findByRole('button', { name: /to review/ }))   // #104: the data-quality strip's link
    expect(await screen.findByText('CRENSHAW BLVD / NOT STATED')).toBeInTheDocument()
    expect(screen.getByText(/No cross street in the report/)).toBeInTheDocument()
    const group = screen.getByText('CRENSHAW BLVD / NOT STATED').closest('li')
    fireEvent.click(within(group).getAllByRole('button', { name: 'Exclude' })[0])
    const why = screen.getByLabelText(/Why exclude all 2 crashes/)
    fireEvent.change(why, { target: { value: 'Parking lot' } })
    fireEvent.click(screen.getByRole('button', { name: 'Exclude 2' }))
    expect(await screen.findByText('Nothing left to review.')).toBeInTheDocument()
    const post = calls.find((c) => c.method === 'POST' && c.path.endsWith('/review/decisions'))
    expect(post.body).toEqual({ crash_ids: ['1', '2'], action: 'exclude', reason: 'Parking lot' })
    await waitFor(() => expect(calls.filter((c) => c.path.endsWith('/profile')).length).toBeGreaterThan(1))   // recounted
    expect(screen.getByRole('button', { name: 'Undo last' })).toBeEnabled()
  })

  it('places a crash at a study intersection (#97)', async () => {
    const REVIEW = { open: 1, can_undo: false, decided: [], intersections: [{ id: 'osm-1', name: 'Marine Avenue', lat: 1, lon: 2 }],
      groups: [{ key: 'CRENSHAW BLVD / MARINE AVE', primary: 'CRENSHAW BLVD', secondary: 'MARINE AVE', count: 1, reasons: { no_coordinates: 1 }, with_suggestion: 0,
        crashes: [{ crash_id: '9', date: '2023-01-02', severity: 'B', primary_road: 'CRENSHAW BL', secondary_road: 'MARINE AV', reason: 'no_coordinates' }] }] }
    const calls = mockApi({ ...routes, 'GET /studies/:id/review': REVIEW,
      'POST /studies/:id/review/decisions': () => ({ decided: 1, review: { ...REVIEW, open: 0, groups: [], can_undo: true } }) })
    renderAt('/s/s1/profile')
    fireEvent.click(await screen.findByRole('button', { name: /to review/ }))   // #104: the data-quality strip's link
    fireEvent.click(await screen.findByRole('button', { name: 'At an intersection' }))
    fireEvent.change(screen.getByLabelText(/Intersection for crash 9/), { target: { value: 'osm-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Place' }))
    await screen.findByText('Nothing left to review.')
    expect(calls.find((c) => c.path.endsWith('/review/decisions')).body)
      .toEqual({ crash_ids: ['9'], action: 'place', method: 'intersection', location_id: 'osm-1' })
  })

  it('fatal crashes come first, red-flagged, with a lookup aid; placing one needs a source (#175)', async () => {
    const F = { crash_id: '7', date: '2023-05-28', hour: 23, severity: 'K', killed: 1, fatal: true, city: 'Hawthorne',
      collision_type: 'VEHICLE/PEDESTRIAN', primary_road: 'CRENSHAW BL', secondary_road: 'NOT STATED', reason: 'no_cross_street',
      fars_hint: { fars_case: '2023-60012', miles_from_corridor: 3.4, lat: 33.9, lon: -118.3 },
      lookup: [{ label: 'News search', url: 'https://news.google.com/search?q=x' }, { label: 'Web search', url: 'https://www.bing.com/search?q=x' }] }
    const REVIEW = { open: 1, fatal_open: 1, fatal: [F], can_undo: false, decided: [], groups: [],
      intersections: [{ id: 'osm-1', name: 'Marine Avenue', lat: 1, lon: 2 }] }
    const calls = mockApi({ ...routes, 'GET /studies/:id/review': REVIEW,
      'POST /studies/:id/review/decisions': () => ({ decided: 1, review: { ...REVIEW, open: 0, fatal_open: 0, fatal: [], can_undo: true } }) })
    renderAt('/s/s1/profile')
    fireEvent.click(await screen.findByRole('button', { name: /to review/ }))
    expect(await screen.findByTestId('fatal-header')).toHaveTextContent('1 fatal crash needs a location')
    const item = screen.getByTestId('fatal-item')
    expect(within(item).getByTestId('fars-hint')).toHaveTextContent('FARS puts this crash 3.4 mi from the corridor')
    const link = within(item).getByRole('link', { name: 'News search' })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(within(item).getByRole('button', { name: 'At an intersection' })).toBeDisabled()   // no source yet
    fireEvent.change(within(item).getByLabelText(/Source for fatal crash 7/), { target: { value: 'Daily Breeze, May 29 2023' } })
    fireEvent.click(within(item).getByRole('button', { name: 'At an intersection' }))
    fireEvent.change(screen.getByLabelText(/Intersection for fatal crash 7/), { target: { value: 'osm-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Place' }))
    await screen.findByText('Nothing left to review.')
    expect(calls.find((c) => c.path.endsWith('/review/decisions')).body).toEqual(
      { crash_ids: ['7'], action: 'place', method: 'intersection', location_id: 'osm-1', source: 'Daily Breeze, May 29 2023' })
  })

  it('drill-down: a study intersection shows its collision diagram, why some crashes are not drawn, and T21 (#106)', async () => {
    const lid = location.location_id
    const DIAG = { width: 820, height: 820, stacks: 1, not_drawn: { no_party_data: 1, no_direction: 0, no_room: 0 },
      steps: [{ op: 'rect_cell', w: 820, h: 820 }, { op: 'line', pts: [[410, 20], [410, 800]], dash: false, w: 3, color: 'arm' },
        { op: 'head', x: 400, y: 300, ang: 0, filled: true, color: 'ink' }, { op: 'circle', x: 400, y: 290, r: 4, fill: 'paper', stroke: 'sev_b', w: 2 },
        { op: 'text', x: 380, y: 340, t: '1', size: 10, bold: true, anchor: 'start', color: 'muted' }],
      legend: { symbols: [{ key: 'rear', label: 'Rear-end', steps: [] }], marks: [{ key: 'O', label: 'Property damage only (crossbar)', steps: [] }] },
      crashes: [] }
    const T21 = { id: `T21@${lid}`, title: 'Collision diagram crashes', provenance: {}, columns: [],
      rows: [{ key: '1', label: '2023-01-02 0800', values: { crash_id: '9', approach: 'NB', type: 'Rear-end', severity: 'B', code: 'CN' } },
        { key: '2', label: '2025-03-04 1700', values: { crash_id: '8', approach: '—', type: 'Not drawn (no direction of travel)', severity: 'O', code: 'CD' } }] }
    mockApi({ ...routes, 'GET /studies/:id/profile/locations/:lid': { ...location, diagram: DIAG, tables: [...location.tables, T21] } })
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const label = table(profile, 'T2').rows.find((r) => r.key === lid).label
    fireEvent.click(screen.getAllByRole('button', { name: label })[0])
    const sec = await screen.findByLabelText('Collision diagram')
    expect(within(sec).getByTestId('collision-diagram')).toBeInTheDocument()
    expect(sec).toHaveTextContent('1 with no party data for their year in this pull')
    expect(sec).toHaveTextContent('Rear-end')
    expect(within(sec).getAllByRole('row')).toHaveLength(3)                    // header + T21's two crashes
  })

  it('a table missing a year of CCRS party data carries its note on the ⓘ (#188)', async () => {
    const note = 'No CCRS party details for 2025 in this pull: road users, heavy trucks, movements and the collision diagram leave out those years\' 12 crashes.'
    const p2 = { ...profile, tables: profile.tables.map((t) => (t.id === 'T19' ? { ...t, note } : t)),
      caveats: [...profile.caveats, { key: 'parties_missing', text: note, limitation: true }] }
    mockApi({ ...routes, 'GET /studies/:id/profile': p2 })
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const src = within(screen.getByLabelText('Pedestrians and bicyclists')).getAllByRole('note')[0]          // the section's T19 mark
    expect(src).toHaveAttribute('title', expect.stringContaining('No CCRS party details for 2025'))
    expect(src.className).toContain('src-note')
    expect(screen.getByLabelText('Data limitations')).toHaveTextContent('No CCRS party details for 2025')   // #269: in the trust line
  })

  it('strip diagram: one dot per placed crash (= T1 crashes), hover, click to drill, color toggle (#102)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const strip = screen.getByLabelText('Crashes along the corridor')
    expect(within(strip).getByText('Where along the corridor crashes bunch up')).toBeInTheDocument()
    const dots = within(strip).getAllByTestId('strip-dot')
    expect(dots.length).toBe(cell(profile, 'T1/crashes/value'))
    fireEvent.mouseEnter(dots[0])
    expect(within(strip).getByRole('tooltip')).toBeInTheDocument()
    fireEvent.click(within(strip).getByRole('radio', { name: 'Collision type' }))
    expect(within(strip).getByRole('radio', { name: 'Collision type' })).toHaveAttribute('aria-checked', 'true')
    expect(within(strip).queryByText('Serious injury')).toBeNull()
    const rows = within(strip).getAllByRole('row').slice(1)            // Show table: one row per T2 location
    expect(rows).toHaveLength(table(profile, 'T2').rows.length)
    table(profile, 'T2').rows.forEach((r, i) => expect(rows[i].lastChild.textContent).toBe(nf.format(r.values.crashes)))
    const first = table(profile, 'T2').rows[0].key                   // the location the fixture's drill-down covers
    fireEvent.click(dots.find((d) => d.getAttribute('data-location') === first))
    expect(await screen.findByText('← All locations')).toBeInTheDocument()
  })

  it('ranks locations from T2: order, numbers, sort toggle, show all, show table (#103)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const rank = screen.getByLabelText('Location ranking')
    expect(within(rank).getByText('Which locations need attention first?')).toBeInTheDocument()
    const t2 = table(profile, 'T2').rows.filter((r) => r.values.crashes > 0)
    const byCrashes = [...t2].sort((a, b) => b.values.crashes - a.values.crashes || a.label.localeCompare(b.label))
    const items = () => within(rank).getAllByRole('listitem')
    expect(items()).toHaveLength(Math.min(5, t2.length))
    items().forEach((li, i) => {
      expect(li.querySelector('.rowlink').textContent).toBe(byCrashes[i].label)
      expect(li.querySelector('.n').textContent).toBe(nf.format(byCrashes[i].values.crashes))
      expect(li.querySelector('.ksi').textContent).toBe(`${nf.format(byCrashes[i].values.ksi_crashes)} KSI`)
    })
    fireEvent.click(within(rank).getByRole('radio', { name: 'KSI' }))
    const byKsi = [...t2].sort((a, b) => b.values.ksi_crashes - a.values.ksi_crashes || b.values.crashes - a.values.crashes || a.label.localeCompare(b.label))
    expect(items()[0].querySelector('.rowlink').textContent).toBe(byKsi[0].label)
    if (t2.length > 5) {
      fireEvent.click(within(rank).getByRole('button', { name: `Show all ${t2.length}` }))
      expect(items()).toHaveLength(t2.length)
    }
    expect(within(rank).queryByRole('radio', { name: 'Rate vs critical' })).toBeNull()   // no AADT in the fixture
    const full = within(rank.querySelector('details')).getAllByRole('row').slice(1)
    expect(full).toHaveLength(table(profile, 'T2').rows.length)
  })

  it('ranks by Caltrans crash cost from T2: order, the cost and its U count (#273)', async () => {
    const costs = { 0: 5233000, 1: 7027000, 2: 475000 }
    const p2 = { ...profile, tables: profile.tables.map((t) => (t.id !== 'T2' ? t : { ...t, rows: t.rows.map((r, i) => (
      { ...r, values: { ...r.values, crash_cost: costs[i] ?? 20000, sev_u: i === 1 ? 2 : 0, cost_control_unknown: i === 0 } })) })) }
    mockApi({ ...routes, 'GET /studies/:id/profile': p2 })
    renderAt('/s/s1/profile')
    const rank = await screen.findByLabelText('Location ranking')
    expect(within(rank).queryByTestId('rank-cost')).toBeNull()                    // the count ranking stays the default
    fireEvent.click(within(rank).getByRole('radio', { name: 'Crash cost' }))
    const t2 = table(p2, 'T2').rows.filter((r) => r.values.crashes > 0)
    const byCost = [...t2].sort((a, b) => b.values.crash_cost - a.values.crash_cost || b.values.crashes - a.values.crashes || a.label.localeCompare(b.label))
    const items = within(rank).getAllByRole('listitem')
    items.forEach((li, i) => expect(li.querySelector('.rowlink').textContent).toBe(byCost[i].label))
    const first = within(items[0]).getByTestId('rank-cost')
    expect(first).toHaveTextContent('$7.0M · 2 U')
    expect(first.getAttribute('title')).toContain('$7,027,000')
  })

  it('severity bars equal T3 and KSI equals T1 (#103)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const sev = screen.getByLabelText('Severity')
    expect(within(sev).getByText('How bad, not just how many?')).toBeInTheDocument()
    expect(sev.querySelector('.ksi-call b').textContent).toBe(nf.format(cell(profile, 'T1/ksi_crashes/value')))
    const t3 = table(profile, 'T3').rows.filter((r) => r.key !== 'U' || r.values.crashes)
    const bars = sev.querySelectorAll('.bars .bar')
    expect(bars).toHaveLength(t3.length)
    t3.forEach((r, i) => {
      expect(bars[i].querySelector('.lab').textContent).toBe(r.label)
      expect(bars[i].querySelector('.v').textContent).toBe(`${nf.format(r.values.crashes)} · ${nf.format(r.values.share_pct)}%`)
    })
  })

  it('year trend: bars equal T11, COVID 2021 shaded, preliminary marked (#104)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const tr = screen.getByLabelText('Crashes by year')
    expect(within(tr).getByText('Getting better or worse?')).toBeInTheDocument()
    const t11 = table(profile, 'T11').rows
    const years = within(tr).getAllByTestId('trend-year')
    expect(years).toHaveLength(t11.length)
    t11.forEach((r, i) => {
      expect(years[i].querySelector('.n').textContent).toBe(nf.format(r.values.crashes))
      expect(years[i].classList.contains('covid')).toBe(r.values.covid === 'Yes')         // docs/03: 2020 and 2021
      expect(Boolean(years[i].querySelector('.prelim'))).toBe(r.values.preliminary > 0)
      const segs = [...years[i].querySelectorAll('.col i')].map((e) => e.className)          // the K/A/B/C/U/O ramp
      expect(segs).toEqual(['k', 'a', 'b', 'c', 'u', 'o'].filter((k) => r.values[`sev_${k}`]).map((k) => `sev-${k}`))
    })
    expect(within(tr).getByText(/COVID-19 changed travel/)).toBeInTheDocument()
  })

  it('data quality strip: T1 parts add up to every crash read; review and excluded links (#104)', async () => {
    mockApi({ ...routes, 'GET /studies/:id/review': { open: 0, groups: [], decided: [], can_undo: false, intersections: [] } })
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const q = screen.getByLabelText('Data quality')
    expect(within(q).getByText('Can I trust these numbers?')).toBeInTheDocument()
    const v = (k) => cell(profile, `T1/${k}/value`)
    expect(v('located_gps') + (v('located_fars') || 0) + v('located_exact') + (v('located_unique_pair') || 0) + (v('located_freeway') || 0) + v('located_other') + (v('user_placed') || 0)).toBe(v('crashes'))
    expect(within(q).getByTestId('q-located_gps').textContent).toContain(nf.format(v('located_gps')))
    const ex = within(q).getByRole('button', { name: new RegExp(`${nf.format(v('excluded'))} nearby, outside the corridor`) })
    fireEvent.click(ex)
    const rules = within(q).getByLabelText('Excluded, by rule')
    const sum = [...rules.querySelectorAll('li .mono')].reduce((t, e) => t + Number(e.textContent.replace(/,/g, '')), 0)
    expect(sum).toBe(v('excluded'))
  })

  it('collision type x location grid equals T13; empty rows and columns hidden (#105)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const g = screen.getByLabelText('Collision type by location')
    expect(within(g).getByText('Is there a pattern?')).toBeInTheDocument()
    const t13 = table(profile, 'T13')
    const cols = t13.columns.filter((c) => c.key !== 'total' && t13.rows.some((r) => r.values[c.key]))
    const rows = t13.rows.filter((r) => r.values.total)
    const body = g.querySelectorAll('tbody tr')
    expect(body).toHaveLength(rows.length)
    rows.forEach((r, i) => {
      expect(body[i].querySelector('th button').getAttribute('title')).toBe(r.label)       // short name shown, full on hover
      const cells = [...body[i].querySelectorAll('td')].map((td) => Number(td.textContent || 0))
      expect(cells).toEqual(cols.map((c) => r.values[c.key] || 0))
    })
    const heads = [...g.querySelectorAll('thead th')].slice(1)
    expect(heads.map((th) => th.getAttribute('title'))).toEqual(cols.map((c) => c.label))
    expect(heads.every((th) => th.textContent.length <= 9)).toBe(true)                          // short headers (#119)
  })

  it('pedestrians and bicyclists: right under the trust strip, numbers equal T19 cells, map toggle filters (#136)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const v = screen.getByLabelText('Pedestrians and bicyclists')
    // right after the summary: trust line, then the top locations (#269)
    expect(screen.getByLabelText('Location ranking').nextElementSibling).toBe(v)
    const t19 = table(profile, 'T19')
    const val = (k) => t19.rows.find((x) => x.key === k).values
    for (const k of ['ped', 'bike', 'ebike', 'escooter', 'motorcycle']) {
      const li = within(v).getByTestId(`vru-${k}`)
      expect(li.querySelector('.n').textContent).toBe(nf.format(val(k).crashes))
      expect(li.querySelector('.ksi').textContent).toBe(`${nf.format(val(k).ksi_crashes)} KSI`)
    }
    const head = within(v).getByTestId('vru-headline').textContent
    expect(head).toContain(`${nf.format(val('ped').crashes)} pedestrian and ${nf.format(val('bike').crashes)} bicycle`)
    const min = profile.min_share_n                                       // small numbers (#271): counts only below it
    if (val('all').ksi_crashes >= min && val('ped_or_bike').crashes) {
      expect(head).toContain(`${nf.format(val('ped_or_bike').share_of_ksi_pct)}%`)
      expect(head).toContain(`(${nf.format(val('ped_or_bike').ksi_crashes)} of ${nf.format(val('all').ksi_crashes)})`)
    } else if (val('ped_or_bike').crashes) {
      expect(head).toContain(`${nf.format(val('ped_or_bike').ksi_crashes)} of the ${nf.format(val('all').ksi_crashes)} crashes`)
    }
    for (const k of ['ped', 'other']) {
      if (!val(k).crashes) continue
      const row = within(v).getByTestId(`danger-${k}`)
      expect(row.querySelector('.nn').textContent).toBe(`${nf.format(val(k).ksi_crashes)} of ${nf.format(val(k).crashes)}`)
      if (val(k).crashes < min) { expect(row.querySelector('.tr')).toBeNull(); continue }
      expect(row.querySelector('.v').textContent).toBe(`${nf.format(val(k).ksi_pct)}%`)
      expect(row.querySelector('.tr i').style.width).toBe(`${val(k).ksi_pct}%`)      // fixed 0-100% scale
    }
    const map = screen.getByTestId('map')
    const before = Number(map.getAttribute('data-n'))
    fireEvent.click(within(within(v).getByTestId('vru-motorcycle')).getByRole('button', { name: 'Show only these on the map' }))
    await waitFor(() => expect(Number(screen.getByTestId('map').getAttribute('data-n'))).toBeLessThan(before))
    expect(within(v).getByRole('button', { name: 'Showing only these on the map' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('ranking: a ped/bike count per location and a sort by it (#136)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const rk = screen.getByLabelText('Location ranking')
    fireEvent.click(within(rk).getByRole('radio', { name: 'Pedestrians + bicyclists' }))
    const t2 = table(profile, 'T2')
    const top = [...t2.rows].filter((r) => r.values.crashes > 0).sort((a, b) => b.values.vru_crashes - a.values.vru_crashes
      || b.values.crashes - a.values.crashes || a.label.localeCompare(b.label))[0]
    const first = rk.querySelector('.rank li')
    expect(first.querySelector('.rowlink').textContent).toBe(top.label)
    expect(first.querySelector('[data-testid="rank-vru"]').textContent).toContain(`${nf.format(top.values.vru_crashes)} ped/bike`)
  })

  it('strip: every pedestrian or bicycle crash has the ring marker, and the legend says so (#136)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const strip = screen.getByLabelText('Crashes along the corridor')
    const placed = new Set(assignment.assignments.filter((a) => a.kind === 'intersection' || a.kind === 'segment').map((a) => a.crash_id))
    const vru = crashes.crashes.filter((c) => placed.has(c.crash_id) && (c.ped || c.bike || c.ebike || c.escooter))
    expect(strip.querySelectorAll('[data-testid="strip-vru"]').length).toBe(vru.length)
    if (vru.length) expect(within(strip).getByText('Ring: pedestrian, bicyclist, e-bike or e-scooter involved')).toBeTruthy()
  })
})

describe('Profile display fixes (#266)', () => {
  it('keeps the KPI value and its "5 yr" sub-label apart (not "1055 yr")', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    const kpis = await screen.findByLabelText('Key numbers')
    const sub = within(kpis).getByText(/^\d+ yr$/)
    const value = sub.closest('.sf-kpi__value')
    expect(value.textContent).toBe(`${nf.format(cell(profile, profile.kpis.crashes))} ${sub.textContent}`)
  })

  function grid(lastRight) {
    // jsdom has no layout: the grid is 800 px wide; its last column ends at lastRight; scrollWidth says 900 either way
    const spy = vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function rect() {
      const right = this.classList?.contains('gridwrap') ? 800 : this.tagName === 'TH' ? lastRight : 0
      return { left: 0, right, top: 0, bottom: 0, width: right, height: 0, x: 0, y: 0 }
    })
    const sw = vi.spyOn(Element.prototype, 'scrollWidth', 'get').mockReturnValue(900)
    const cw = vi.spyOn(Element.prototype, 'clientWidth', 'get').mockReturnValue(800)
    return () => { spy.mockRestore(); sw.mockRestore(); cw.mockRestore() }
  }

  it('says "More columns" only when a column is past the right edge', async () => {
    const restore = grid(800)                                 // every column visible
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Collision type by location')
    await new Promise((r) => setTimeout(r, 50))              // let the overflow check run
    expect(screen.queryByText(/More columns/)).toBeNull()
    restore()
  })

  it('says "More columns" when one is hidden', async () => {
    const restore = grid(950)                                 // the last column ends 150 px past the edge
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Collision type by location')
    expect(await screen.findByText(/More columns/)).toBeInTheDocument()
    restore()
  })
})

// #265: the safety tables the backend already computes. safety_tables.json holds T18 (PCF in the 24 SWITRS categories),
// T14, T16, T17 and their @location tables as tests/fixtures/make_frontend_fixtures.py writes them at this commit; the
// other fixtures predate them.
import safety from '../__fixtures__/safety_tables.json'

describe('Safety tables on tab 3 (#265)', () => {
  const sp = { ...profile, tables: [...profile.tables, ...safety.profile] }
  const sloc = { ...location, tables: [...location.tables, ...safety.location] }
  const sroutes = { ...routes, 'GET /studies/:id/profile': sp, 'GET /studies/:id/profile/locations/:lid': sloc }
  const t = (id) => table(sp, id)

  it('"Why did they crash?": one PCF bar per T18 row, sorted as T18, numbers from its cells, a table on demand', async () => {
    mockApi(sroutes)
    renderAt('/s/s1/profile')
    const sec = await screen.findByLabelText('Why did they crash?')
    const bars = within(sec).getAllByTestId('pcf-bar')
    expect(bars).toHaveLength(t('T18').rows.length)
    t('T18').rows.forEach((r, i) => {
      expect(bars[i]).toHaveTextContent(r.label)
      expect(bars[i]).toHaveTextContent(nf.format(r.values.crashes))
    })
    expect(within(sec).getAllByLabelText('Source: table T18').length).toBeGreaterThan(0)
    const tbl = within(sec).getByText('Show table').closest('details')
    const rows = within(tbl).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(t('T18').rows.length)
    expect(within(rows[0]).getAllByRole('cell').map((c) => c.textContent))
      .toEqual(['crashes', 'ksi_crashes', 'share_pct'].map((k) => nf.format(t('T18').rows[0].values[k])))
  })

  it('"Why did they crash?" comes after severity and before the trend (#269)', async () => {
    mockApi(sroutes)
    renderAt('/s/s1/profile')
    const why = await screen.findByLabelText('Why did they crash?')
    const after = (a, b) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING)
    expect(after(screen.getByLabelText('Severity'), why)).toBe(true)
    expect(after(why, screen.getByLabelText('Crashes by year'))).toBe(true)
  })

  it('hit and run, DUI and speed from T14, each with its source mark', async () => {
    mockApi(sroutes)
    renderAt('/s/s1/profile')
    const blk = await screen.findByLabelText('Hit and run, DUI and speed')
    for (const r of t('T14').rows) expect(blk).toHaveTextContent(`${r.label.trim()}`)
    expect(within(blk).getAllByTestId('flag-row').map((e) => e.querySelector('.v').textContent))
      .toEqual(t('T14').rows.map((r) => nf.format(r.values.crashes)))
    expect(within(blk).getAllByLabelText('Source: table T14')).toHaveLength(1)
  })

  it('left turn vs right angle (T17) under Collision type, as shares of broadside', async () => {
    mockApi(sroutes)
    renderAt('/s/s1/profile')
    const blk = await screen.findByLabelText('Broadside: left turn vs right angle')
    for (const r of t('T17').rows) expect(blk).toHaveTextContent(`${nf.format(r.values.share_pct)}%`)
    expect(within(blk).getByLabelText('Source: table T17')).toBeInTheDocument()
  })

  it('Conditions: movement, weather, surface and lighting, folded by default', async () => {
    mockApi(sroutes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const det = screen.getByText('Conditions').closest('details')
    expect(det.open).toBe(false)
    for (const [id, name] of [['T16', 'Movement before the collision (party at fault)'], ['T7', 'Weather'],
      ['T8', 'Road surface'], ['T6', 'Lighting']]) {
      expect(within(det).getByRole('heading', { name })).toBeInTheDocument()
      expect(within(det).getAllByLabelText(`Source: table ${id}`).length).toBeGreaterThan(0)
      for (const r of t(id).rows) expect(within(det).getAllByText(r.label.trim()).length).toBeGreaterThan(0)
    }
  })

  it('empty tables hide their block', async () => {
    const zero = (x) => ({ ...x, rows: x.rows.map((r) => ({ ...r, values: { ...r.values, crashes: 0 } })) })
    const ep = { ...sp, tables: sp.tables.filter((x) => x.id !== 'T18').map((x) => (x.id === 'T14' || x.id === 'T17' ? zero(x) : x)) }
    mockApi({ ...sroutes, 'GET /studies/:id/profile': ep })
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    expect(screen.queryByLabelText('Why did they crash?')).toBeNull()
    expect(screen.queryByLabelText('Hit and run, DUI and speed')).toBeNull()
    expect(screen.queryByLabelText('Broadside: left turn vs right angle')).toBeNull()
  })

  it('a table missing a year carries its red note on the new blocks too (#188)', async () => {
    const note = 'No CCRS party details for 2025 in this pull.'
    const np = { ...sp, tables: sp.tables.map((x) => (x.id === 'T16' ? { ...x, note } : x)) }
    mockApi({ ...sroutes, 'GET /studies/:id/profile': np })
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const det = screen.getByText('Conditions').closest('details')
    const src = within(det).getAllByLabelText(/Source: table T16/)[0]
    expect(src.className).toContain('src-note')
  })

  it('the location drill-in shows its PCF categories and hit and run / DUI / speed', async () => {
    mockApi(sroutes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const first = table(profile, 'T2').rows[0]
    fireEvent.click(within(screen.getByLabelText('Location ranking')).getAllByRole('button', { name: first.label })[0])
    await screen.findByText('← All locations')
    const pcf = table(sloc, `T18@${first.key}`)
    const sec = screen.getByLabelText('Why did they crash? (this location)')
    expect(within(sec).getAllByTestId('pcf-bar')).toHaveLength(pcf.rows.length)
    expect(screen.getByLabelText('Hit and run, DUI and speed (this location)')).toBeInTheDocument()
  })
})

describe('Small numbers on the safety blocks (#265, user decision 2026-10-25)', () => {
  it('a base under 10 crashes shows counts only, "2 of 4", a too-few note, no share and no bar; zero rows hidden in the drill-in', async () => {
    const first = table(profile, 'T2').rows[0]
    const t14 = safety.location.find((x) => x.id.startsWith('T14@'))
    const small = { ...t14, id: `T14@${first.key}`, rows: [
      { key: 'hit_and_run', label: 'Hit and run (felony or misdemeanor)', values: { crashes: 2, ksi_crashes: 0, share_pct: 50 } },
      { key: 'dui', label: 'Driving under the influence (PCF VC 23152 / 23153)', values: { crashes: 0, ksi_crashes: 0, share_pct: 0 } }] }
    const sloc = { ...location, tables: [...location.tables.filter((x) => !x.id.startsWith('T14@')), small] }
    const sp = { ...profile, tables: [...profile.tables, ...safety.profile] }
    const T2 = { ...table(profile, 'T2') }
    const p4 = { ...sp, tables: sp.tables.map((x) => (x.id === 'T2' ? { ...T2, rows: T2.rows.map((r, i) => (i ? r : { ...r, values: { ...r.values, crashes: 4 } })) } : x)) }
    mockApi({ ...routes, 'GET /studies/:id/profile': p4, 'GET /studies/:id/profile/locations/:lid': sloc })
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    fireEvent.click(within(screen.getByLabelText('Location ranking')).getAllByRole('button', { name: first.label })[0])
    const blk = await screen.findByLabelText('Hit and run, DUI and speed (this location)')
    const rows = within(blk).getAllByTestId('flag-row')
    expect(rows).toHaveLength(1)                                      // the zero DUI row is hidden here
    expect(rows[0]).toHaveTextContent('2 of 4')
    expect(blk).not.toHaveTextContent('%')
    expect(rows[0].querySelector('.tr')).toBeNull()
    expect(blk).toHaveTextContent('Too few to compare')
  })

  it('the broadside split under 10 broadside crashes shows "x of n", no percentages', async () => {
    const sp = { ...profile, tables: [...profile.tables, ...safety.profile] }
    const few = sp.tables.map((x) => (x.id === 'T17' ? { ...x, rows: [
      { key: 'left_turn', label: 'Left turn (a party was making a left turn)', values: { crashes: 3, ksi_crashes: 0, share_pct: 75 } },
      { key: 'right_angle', label: 'Right angle (no party turning left)', values: { crashes: 1, ksi_crashes: 0, share_pct: 25 } }] } : x))
    mockApi({ ...routes, 'GET /studies/:id/profile': { ...sp, tables: few } })
    renderAt('/s/s1/profile')
    const blk = await screen.findByLabelText('Broadside: left turn vs right angle')
    expect(blk).toHaveTextContent('left turn 3 of 4')
    expect(blk).not.toHaveTextContent('%')
    expect(blk).toHaveTextContent('Too few to compare')
  })
})

// #271, user decision 2026-10-25: a share on fewer than min_share_n crashes (from the server) is a count only
describe('Small numbers on tab 3 (#271)', () => {
  const withN = (p) => ({ ...p, min_share_n: 10 })
  const setT = (p, id, f) => ({ ...p, tables: p.tables.map((t) => (t.id === id ? f(t) : t)) })
  const setRow = (t, key, vals) => ({ ...t, rows: t.rows.map((r) => (r.key === key ? { ...r, values: { ...r.values, ...vals } } : r)) })
  const render = async (p) => {
    mockApi({ ...routes, 'GET /studies/:id/profile': withN(p) })
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
  }

  it('danger bars: base 9 is a count with no bar and no %; base 10 has its bar', async () => {
    await render(setT(setT(profile, 'T19', (t) => setRow(setRow(t, 'ped', { crashes: 9, ksi_crashes: 1, ksi_pct: 11.1 }),
      'motorcycle', { crashes: 10, ksi_crashes: 1, ksi_pct: 10 })), 'T1', (t) => t))
    const ped = screen.getByTestId('danger-ped'), moto = screen.getByTestId('danger-motorcycle')
    expect(ped.querySelector('.tr')).toBeNull()
    expect(ped).not.toHaveTextContent('%')
    expect(ped).toHaveTextContent('1 of 9')
    expect(moto.querySelector('.tr')).not.toBeNull()
    expect(moto).toHaveTextContent('10%')
    expect(screen.getByTestId('danger')).toHaveTextContent('Too few to compare')
  })

  it('the headline percentage needs 10 KSI crashes; with 7 it says the counts only', async () => {
    await render(profile)                                                  // the fixture has 7 KSI crashes
    const h = screen.getByTestId('vru-headline')
    expect(h.querySelector('b')).toBeNull()
    expect(h).not.toHaveTextContent(/\d%.*of all crashes that killed/)
  })

  it('severity: a total of 9 is counts only ("2 of 9"), no bars', async () => {
    const t3rows = [['K', 0], ['A', 2], ['B', 2], ['C', 1], ['U', 0], ['O', 4]]
    await render(setT(profile, 'T3', (t) => t3rows.reduce((acc, [k, n]) => setRow(acc, k, { crashes: n }), t)))
    const sec = screen.getByLabelText('Severity')
    expect(sec.querySelectorAll('.sevsum .tr')).toHaveLength(0)
    expect(sec).toHaveTextContent('2 of 9')
    expect(sec).toHaveTextContent('Too few to compare')
  })

  it('pedestrian day/night: 2 pedestrian crashes are counts only; the table behind marks them n < 10', async () => {
    const p = setT(profile, 'T20', (t) => ({ ...t, columns: [...t.columns, { key: 'small_base', label: 'Base' }],
      rows: t.rows.map((r) => ({ ...r, values: { ...r.values, small_base: 'n < 10' } })) }))
    await render(p)
    const ctx = screen.getByTestId('ped-daynight')
    expect(ctx.querySelectorAll('.tr')).toHaveLength(0)
    expect(ctx).toHaveTextContent('1 of 2')
    const sec = screen.getByLabelText('Pedestrians and bicyclists')
    expect(within(sec.querySelector('details.showtable')).getAllByText('n < 10').length).toBeGreaterThan(0)
  })
})

// #287: state-highway crash rates from Caltrans AADT (T22 by segment, T23 by year), every row citing its count years
describe('State-highway crash rates (#287)', () => {
  const T22 = { id: 'T22', title: 'State-highway crash rates (Caltrans AADT; crashes per million vehicle-miles)', columns: [],
    provenance: {}, rows: [
      { key: 'seg-a', label: 'EL CAMINO REAL – SANCHEZ AVENUE', values: { crashes: 30, fi_crashes: 12, fatal_crashes: 1, length_mi: 0.6, aadt: 120000, mvm: 131.4,
        rate_all: 0.23, rate_fi: 0.09, rate_fatal: 0.01, corridor_rate_all: 0.2, ratio_to_corridor: 1.15,
        count_years: '2021–2024; later count years use 2024', source: 'Caltrans Traffic Census Program' } },
      { key: 'seg-b', label: 'B – C', values: { crashes: 10, fi_crashes: 3, fatal_crashes: 0, length_mi: 0.4, aadt: 110000, mvm: 80.3,
        rate_all: 0.12, rate_fi: 0.04, rate_fatal: 0, corridor_rate_all: 0.2, ratio_to_corridor: 0.6,
        count_years: '2021–2024; later count years use 2024', source: 'Caltrans Traffic Census Program' } },
      { key: 'seg-c', label: 'C – D', values: { crashes: 2, fi_crashes: 1, fatal_crashes: 0, length_mi: 0.1, aadt: 100000, mvm: 18.3,
        rate_all: 0.11, rate_fi: 0.05, rate_fatal: 0, corridor_rate_all: 0.2, ratio_to_corridor: 1.5, small_base: 'n < 10: segment',
        count_years: '2021–2024; later count years use 2024', source: 'Caltrans Traffic Census Program' } }],
    scope: { rated_crashes: 42, ramp_crashes: 7, cross_street_crashes: 12, corridor_rate_all: 0.2, small: false,
      text: 'Mainline crashes: 42. Not in this rate: 7 ramp crashes (see Ramps), 12 cross-street crashes.' } }
  const T23 = { id: 'T23', title: 'State-highway crash rate by year', columns: [], provenance: {}, rows: [
    { key: '2021', label: '2021', values: { crashes: 9, fi_crashes: 3, mvm: 42.1, rate_all: 0.21, rate_fi: 0.07 } },
    { key: '2022', label: '2022', values: { crashes: 12, fi_crashes: 2, mvm: 42.3, rate_all: 0.28, rate_fi: 0.05 } }] }
  T23.rows[0].values.small_base = 'n < 10'

  it('shows each segment\'s rates from T22 against the corridor average, with the AADT years and source', async () => {
    mockApi({ ...routes, 'GET /studies/:id/profile': { ...profile, tables: [...profile.tables, T22, T23] } })
    renderAt('/s/s1/profile')
    const sec = await screen.findByLabelText('State-highway crash rates')
    const rows = within(sec.querySelector('[data-testid="shs-rates"]')).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(3)
    expect(within(rows[0]).getByRole('rowheader')).toHaveTextContent('El Camino Real – Sanchez Avenue')
    // the inputs an engineer checks first are columns; MVM, fatal and the corridor average are in the detail table
    expect(within(rows[0]).getAllByRole('cell').map((c) => c.textContent)).toEqual(['30', '120,000', '0.6', '0.23', '0.09', '1.15'])
    expect(rows[0]).toHaveClass('over')                                           // above the corridor average
    expect(rows[1]).not.toHaveClass('over')
    expect(sec).toHaveTextContent('AADT: Caltrans Traffic Census Program, count years 2021–2024; later count years use 2024.')
    expect(sec.textContent.match(/count years/g)).toHaveLength(2)                // once in the header, once for "later"
    expect(sec).toHaveTextContent('Corridor average 0.2 crashes per MVM')
    expect(sec).toHaveTextContent('Mainline crashes: 42. Not in this rate: 7 ramp crashes (see Ramps), 12 cross-street crashes.')
    expect(within(sec).getAllByLabelText('Source: table T22').length).toBeGreaterThan(0)
    const by = within(sec.querySelector('[data-testid="shs-by-year"]')).getAllByRole('row').slice(1)
    expect(by.map((r) => r.firstChild.textContent)).toEqual(['2021', '2022'])
    expect(within(by[0]).getAllByRole('cell').map((c) => c.textContent)).toEqual(['2021', '9', '42.1', '–', '–'])
    const full = within(sec.querySelector('[data-testid="shs-detail"]')).getAllByRole('row')
    expect(within(full[0]).getAllByRole('columnheader').map((c) => c.textContent)).toContain('MVM')
    expect(within(full[3]).getAllByRole('cell').map((c) => c.textContent)).toContain('n < 10: segment')
  })

  it('a segment with fewer than 10 crashes shows its count only: no rate, ratio or above-average mark', async () => {
    mockApi({ ...routes, 'GET /studies/:id/profile': { ...profile, tables: [...profile.tables, T22, T23] } })
    renderAt('/s/s1/profile')
    const sec = await screen.findByLabelText('State-highway crash rates')
    const row = within(sec.querySelector('[data-testid="shs-rates"]')).getAllByRole('row')[3]
    expect(within(row).getAllByRole('cell').map((c) => c.textContent)).toEqual(['2', '100,000', '0.1', '–', '–', 'too few to compare'])
    expect(row).not.toHaveClass('over')                                           // ratio 1.5, but on 2 crashes
  })

  it('a corridor average on fewer than 10 crashes is too few to compare', async () => {
    const small = { ...T22, scope: { ...T22.scope, small: true, rated_crashes: 2 }, rows: [T22.rows[2]] }
    mockApi({ ...routes, 'GET /studies/:id/profile': { ...profile, tables: [...profile.tables, small, T23] } })
    renderAt('/s/s1/profile')
    const sec = await screen.findByLabelText('State-highway crash rates')
    expect(sec).toHaveTextContent('Corridor average: too few crashes to compare (2)')
  })

  it('shows truck-involved rates per million 3+ axle truck-miles from T24, small segments as counts only', async () => {
    const T24 = { id: 'T24', title: 'State-highway truck-involved crash rates', columns: [], provenance: {},
      scope: { rated_crashes: 14, corridor_rate_truck: 1.1, small: false, text: 'Crashes involving a heavy truck per truck-mile.' }, rows: [
        { key: 'seg-a', label: 'A – B', values: { truck_crashes: 12, length_mi: 0.6, trucks_3plus: 5185, truck_mvm: 5.68,
          rate_truck: 2.11, corridor_rate_truck: 1.1, ratio_to_corridor: 1.92, count_years: '2021–2024', source: 'Caltrans Traffic Census Program' } },
        { key: 'seg-b', label: 'B – C', values: { truck_crashes: 2, length_mi: 0.4, trucks_3plus: 4800, truck_mvm: 3.5,
          rate_truck: 0.57, corridor_rate_truck: 1.1, ratio_to_corridor: 0.52, small_base: 'n < 10: segment',
          count_years: '2021–2024', source: 'Caltrans Traffic Census Program' } }] }
    mockApi({ ...routes, 'GET /studies/:id/profile': { ...profile, tables: [...profile.tables, T22, T23, T24] } })
    renderAt('/s/s1/profile')
    const sec = await screen.findByLabelText('State-highway crash rates')
    const rows = within(sec.querySelector('[data-testid="shs-trucks"]')).getAllByRole('row').slice(1)
    expect(within(rows[0]).getAllByRole('cell').map((c) => c.textContent)).toEqual(['12', '5,185', '2.11', '1.92'])
    expect(rows[0]).toHaveClass('over')
    expect(within(rows[1]).getAllByRole('cell').map((c) => c.textContent)).toEqual(['2', '4,800', '–', 'too few to compare'])
    expect(sec).toHaveTextContent('Corridor truck average 1.1 per million truck-miles')
    expect(within(sec).getByTestId('shs-trucks-scope')).toHaveTextContent('Crashes involving a heavy truck per truck-mile.')
    expect(within(sec).getAllByLabelText('Source: table T24').length).toBeGreaterThan(0)
  })

  it('shows identified ramps from T25 per million vehicles, with every ramp crash outcome counted', async () => {
    const T25 = { id: 'T25', title: 'Ramp crash rates', columns: [], provenance: {}, rows: [
      { key: 'r1', label: 'SB OFF TO VERMONT AVE', values: { crashes: 12, fi_crashes: 4, postmile: 'LA-405 PM 13.492', adt: 4780, mv: 8.72,
        rate_all: 1.38, rate_fi: 0.46, count_years: '2021–2023 (2024, 2025 use 2023)', picked: 0, source: 'Caltrans Traffic Census Program, District 7 ramp ADT' } },
      { key: 'r2', label: 'NB OFF TO NORMANDIE AVE', values: { crashes: 3, fi_crashes: 1, postmile: 'LA-405 PM 13.707', adt: 8156, mv: 14.9,
        rate_all: 0.2, rate_fi: 0.07, count_years: '2021–2024', picked: 1, small_base: 'n < 10', source: 'Caltrans Traffic Census Program, District 7 ramp ADT' } }],
      scope: { ramp_crashes: 20, identified: 15, pick: 2, none: 3, none_why: { 'no cross street': 3 },
        text: '20 ramp crashes: 15 on an identified Caltrans ramp; 2 with 2 or more possible ramps (the engineer picks); 3 with no ramp rate (no cross street: 3).' } }
    mockApi({ ...routes, 'GET /studies/:id/profile': { ...profile, tables: [...profile.tables, T22, T23, T25] } })
    renderAt('/s/s1/profile')
    const sec = await screen.findByLabelText('Ramp crash rates')
    const rows = within(sec.querySelector('[data-testid="shs-ramps"]')).getAllByRole('row').slice(1)
    expect(within(rows[0]).getByRole('rowheader')).toHaveTextContent('SB off to Vermont Ave')
    expect(within(rows[0]).getByRole('rowheader')).toHaveTextContent('LA-405 PM 13.492')
    expect(within(rows[0]).getAllByRole('cell').map((c) => c.textContent)).toEqual(['12', '4,780', '1.38', '2021–2023 (2024, 2025 use 2023)'])
    expect(within(rows[1]).getAllByRole('cell').map((c) => c.textContent)).toEqual(['3', '8,156', '–', '2021–2024'])
    expect(sec).toHaveTextContent('20 ramp crashes: 15 on an identified Caltrans ramp; 2 with 2 or more possible ramps')
    expect(within(sec).getAllByLabelText('Source: table T25').length).toBeGreaterThan(0)
  })

  it('a corridor without T22 shows no state-highway rates', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    expect(screen.queryByLabelText('State-highway crash rates')).toBeNull()
  })
})

describe('State-highway rate names (#346)', () => {
  it('row names override the design system\'s uppercase mono header style, like the ranking list', async () => {
    const { readFileSync } = await import('node:fs')
    const { resolve } = await import('node:path')
    const css = readFileSync(resolve(process.cwd(), 'src/styles/profile.css'), 'utf8')
    const rule = css.match(/\.sf-table\.shs th\[scope="row"\] \{([^}]*)\}/)
    expect(rule).not.toBeNull()
    expect(rule[1]).toContain('text-transform: none')
    expect(rule[1]).toContain('var(--font-body)')
  })
})

// #287 part 1: the engineer picks a Caltrans rate group; the server's expected rate shows, labelled approximate
describe('Statewide average from the Caltrans rate group (#287 part 1)', () => {
  const GROUPS = { source: 'Caltrans, 2024 Crash Data on California State Highways, Basic Average Crash Rate Table', groups: [
    { group: 'H09', kind: 'highway', label: 'Conventional 2 lanes or less, design speed >55, suburban', base_rate: 0.65, adt_factor: 0.02, adt_op: '*', pct_fatal: 1.6, pct_fi: 40.5, printed_page: 83 },
    { group: 'I14', kind: 'intersection', label: 'Intersection F, M and S, signals, urban', base_rate: 0.33, adt_factor: 0, adt_op: '', pct_fatal: 0.6, pct_fi: 48.3, printed_page: 86 },
    { group: 'R10', kind: 'ramp', label: 'Ramp diamond, 1-4 areas, off, urban', base_rate: 1.04, adt_factor: 0, adt_op: '', pct_fatal: 0.3, pct_fi: 36.7, printed_page: 88 }] }
  const statewide = { approximate: true, source: 'Caltrans, 2024 Crash Data on California State Highways, Basic Average Crash Rate Table (pp. 83–90)',
    text: 'Statewide averages are Caltrans\' expected rates for the rate group the engineer entered (base rate + ADT factor). The comparison is approximate.' }
  const T22 = { id: 'T22', title: 'State-highway crash rates', columns: [], provenance: {}, statewide, scope: { rated_crashes: 30, corridor_rate_all: 0.23 }, rows: [
    { key: 'S1', label: 'A – B', values: { crashes: 30, aadt: 20000, length_mi: 0.6, mvm: 21.9, rate_all: 1.37, rate_fi: 0.5, ratio_to_corridor: 1,
      count_years: '2021–2024', source: 'Caltrans Traffic Census Program', rate_group: 'H09', statewide_rate_all: 1.05, statewide_rate_fi: 0.43,
      statewide_rate_fatal: 0.02, ratio_to_statewide: 1.3 } },
    { key: 'S2', label: 'B – C', values: { crashes: 12, aadt: 20000, length_mi: 0.4, mvm: 14.6, rate_all: 0.82, rate_fi: 0.3, ratio_to_corridor: 0.6,
      count_years: '2021–2024', source: 'Caltrans Traffic Census Program' } }] }
  const withT22 = (t22 = T22) => ({ ...profile, tables: [...profile.tables, t22] })

  it('picks a segment\'s rate group with a select, sends it, and shows the statewide rate and ratio with the approximate note', async () => {
    const calls = mockApi({ ...routes, 'GET /studies/:id/profile': withT22(), 'GET /reference/rate-groups': GROUPS,
      'PUT /studies/:id/rate-groups/:kind/:ref': network })
    renderAt('/s/s1/profile')
    const sec = await screen.findByLabelText('State-highway crash rates')
    const sel = await within(sec).findByLabelText('Caltrans rate group, A – B')
    expect(sel).toHaveValue('H09')
    expect(within(sel).getAllByRole('option').map((o) => o.textContent)).toEqual(['Rate group…', 'H09 · Conventional 2 lanes or less, design speed >55, suburban'])
    const rows = within(sec.querySelector('[data-testid="shs-rates"]')).getAllByRole('row')
    expect(within(rows[0]).getAllByRole('columnheader').map((c) => c.textContent).slice(-3)).toEqual(['Rate group', 'Statewide / MVM', '÷ statewide'])
    expect(within(rows[1]).getAllByRole('cell').map((c) => c.textContent).slice(-2)).toEqual(['1.05', '1.3'])
    expect(within(rows[2]).getAllByRole('cell').map((c) => c.textContent).slice(-2)).toEqual(['—', '–'])
    expect(within(sec).getByTestId('statewide-T22')).toHaveTextContent('Approximate.')
    expect(within(sec).getByTestId('statewide-T22')).toHaveTextContent('(pp. 83–90)')

    fireEvent.change(within(sec).getByLabelText('Caltrans rate group, B – C'), { target: { value: 'H09' } })
    await waitFor(() => expect(calls.some((c) => c.method === 'PUT')).toBe(true))
    expect(calls.find((c) => c.method === 'PUT')).toEqual({ method: 'PUT', path: '/studies/s1/rate-groups/segment/S2', body: { rate_group: 'H09' } })
  })

  it('without the rate-group list there is no picker and no statewide column', async () => {
    mockApi({ ...routes, 'GET /studies/:id/profile': withT22({ ...T22, statewide: undefined }) })
    renderAt('/s/s1/profile')
    const sec = await screen.findByLabelText('State-highway crash rates')
    expect(within(sec).queryByLabelText('Caltrans rate group, A – B')).toBeNull()
    expect(within(sec).queryByText('Statewide / MVM')).toBeNull()
  })

  it('offers intersection groups for the corridor\'s intersections, and ramp groups on each ramp', async () => {
    const T25 = { id: 'T25', title: 'Ramp crash rates', columns: [], provenance: {}, scope: { text: '' }, rows: [
      { key: 'r1', label: 'SB OFF TO VERMONT AVE', values: { crashes: 12, postmile: 'LA-405 PM 13.492', adt: 4780, mv: 8.72, rate_all: 1.38,
        count_years: '2021–2023', source: 'x' } }] }
    const calls = mockApi({ ...routes, 'GET /studies/:id/profile': { ...withT22(), tables: [...withT22().tables, T25] },
      'GET /reference/rate-groups': GROUPS, 'PUT /studies/:id/rate-groups/:kind/:ref': network })
    renderAt('/s/s1/profile')
    const ramps = await screen.findByLabelText('Ramp crash rates')
    const sel = await within(ramps).findByLabelText('Caltrans rate group, SB off to Vermont Ave')
    expect(within(sel).getAllByRole('option').map((o) => o.value)).toEqual(['', 'R10'])
    fireEvent.change(sel, { target: { value: 'R10' } })
    await waitFor(() => expect(calls.some((c) => c.method === 'PUT')).toBe(true))
    expect(calls.find((c) => c.method === 'PUT').path).toBe('/studies/s1/rate-groups/ramp/r1')
    const ints = screen.getByTestId('shs-intersections')
    const first = within(ints).getAllByRole('combobox')[0]
    expect(within(first).getAllByRole('option').map((o) => o.value)).toEqual(['', 'I14'])
  })
})
