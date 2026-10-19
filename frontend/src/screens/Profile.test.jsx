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
})
