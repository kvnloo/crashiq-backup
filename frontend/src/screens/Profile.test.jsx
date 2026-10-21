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
  it('shows at most 4 KPIs and every KPI equals its T1 cell', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    const kpis = await screen.findByLabelText('Key numbers')
    const values = within(kpis).getAllByText((_, el) => el.classList?.contains('sf-kpi__value'))
    expect(values).toHaveLength(4)
    const expected = Object.values(profile.kpis).map((a) => nf.format(cell(profile, a)))
    values.forEach((el, i) => expect(el.textContent.startsWith(expected[i])).toBe(true))
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
    for (const r of table(profile, 'T4').rows) expect(screen.getAllByText(r.label).length).toBeGreaterThan(0)
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
    expect(v('located_gps') + v('located_exact') + v('located_other') + (v('user_placed') || 0)).toBe(v('crashes'))
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

  it('vulnerable road users: counts and KSI equal T10, top locations from T2, map toggle filters (#105)', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const v = screen.getByLabelText('Vulnerable road users')
    const t10 = table(profile, 'T10')
    for (const k of ['ped', 'bike', 'motorcycle']) {
      const r = t10.rows.find((x) => x.key === k)
      const li = within(v).getByTestId(`vru-${k}`)
      expect(li.querySelector('.n').textContent).toBe(nf.format(r.values.crashes))
      expect(li.querySelector('.ksi').textContent).toBe(`${nf.format(r.values.ksi_crashes)} KSI`)
    }
    const map = screen.getByTestId('map')
    const before = Number(map.getAttribute('data-n'))
    fireEvent.click(within(within(v).getByTestId('vru-motorcycle')).getByRole('button', { name: 'Show on map' }))
    await waitFor(() => expect(Number(screen.getByTestId('map').getAttribute('data-n'))).toBeLessThan(before))
    expect(within(v).getByRole('button', { name: 'Showing on map' })).toHaveAttribute('aria-pressed', 'true')
  })
})
