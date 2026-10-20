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
    const rows = screen.getAllByRole('row').filter((r) => within(r).queryByRole('button'))
    expect(rows).toHaveLength(t2.rows.length)
    t2.rows.forEach((r, i) => {
      const cells = within(rows[i]).getAllByRole('cell').map((c) => c.textContent)
      expect(cells[0]).toContain(r.label)
      expect(cells.slice(1, 6)).toEqual(['crashes', 'ksi_crashes', 'injury_crashes', 'dark_crashes', 'crashes_per_year']
        .map((k) => nf.format(r.values[k])))
    })
    for (const r of table(profile, 'T4').rows) expect(screen.getByText(r.label)).toBeInTheDocument()
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
    expect(screen.queryByText(/COVID/)).toBeNull()                       // window 2021–2025
    const details = screen.getByText('Where these crashes come from').closest('details')
    expect(details.open).toBe(false)
    expect(within(details).getByText('Not placed yet (no coordinates)')).toBeInTheDocument()
  })

  it('drills into a location', async () => {
    mockApi(routes)
    renderAt('/s/s1/profile')
    await screen.findByLabelText('Key numbers')
    const first = table(profile, 'T2').rows[0]
    fireEvent.click(screen.getByRole('button', { name: first.label }))
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
    fireEvent.click(await screen.findByRole('button', { name: 'Review them →' }))
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
    fireEvent.click(await screen.findByRole('button', { name: 'Review them →' }))
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
})
