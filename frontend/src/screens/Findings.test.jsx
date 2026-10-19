import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeAll, describe, expect, it } from 'vitest'
import { META, mockApi, renderAt } from '../test-utils'

beforeAll(() => { HTMLCanvasElement.prototype.getContext = () => null })   // jsdom has no canvas

const STUDY = { id: 's1', name: 'Crenshaw', mode: 'tis', from_year: 2021, to_year: 2025, radius_ft: 250, buffer_ft: 100,
  progress: { corridor: true, crashes: true } }
const F1 = {
  id: 'c7-osm_1029_dark', location_id: 'osm-1029', source: 'screen', status: 'proposed',
  title: 'Crashes after dark over-represented at West 135th Street',
  text: 'Crashes after dark are over-represented at West 135th Street: 12 of 20 crashes here (60%) vs 36.2% across the corridor intersections.',
  numbers: [
    { value: 12, table_id: 'T12', cell: 'osm-1029~dark/target_crashes' },
    { value: 20, table_id: 'T12', cell: 'osm-1029~dark/location_crashes' },
    { value: 60, table_id: 'T12', cell: 'osm-1029~dark/share_pct' },
    { value: 36.2, table_id: 'T12', cell: 'osm-1029~dark/reference_share_pct' }],
  pattern_ref: 'HSM Part B, Ch. 6 diagnosis: nighttime collisions', evidence_refs: { tables: ['T12'], records: {} },
  meta: { strength: 'Strong', probability: 0.97, method: 'HSM excess proportion (beta prior from reference sites)', excess_pct: 23.8,
    corridor_crashes: 105, reference: 'corridor intersections', reference_crashes: 80, pattern: 'dark', location: 'West 135th Street', kind: 'intersection', library_status: 'draft' },
}
const F2 = { ...F1, id: 'c7-seg_x_type_broadside', title: 'Broadside crashes over-represented at Marine Avenue – West 147th Street',
  meta: { ...F1.meta, strength: 'Moderate', pattern: 'type_broadside', location: 'Marine Avenue – West 147th Street', kind: 'segment' } }
const LIB = { status: 'draft', entries: {
  dark: { ref: 'HSM Part B, Ch. 6 diagnosis: nighttime collisions', anim: 'night', factors: ['Poor visibility or lighting'], verify: 'Night visit.' },
  type_broadside: { ref: 'HSM Part B, Ch. 6 diagnosis: right-angle collisions', anim: 'broadside', factors: ['Red-light running'], verify: 'Check signals.' } } }
const RECS = Array.from({ length: 12 }, (_, i) => ({ crash_id: `c${i}`, date: '2023-01-0' + (i % 9 + 1), hour: 21, collision_type: 'REAR END',
  severity: i === 0 ? 'A' : 'O', lighting: 'DARK - STREET LIGHTS', primary_road: 'CRENSHAW BL', secondary_road: '135TH ST' }))

function routes(extra = {}) {
  return { 'GET /studies/meta': META, 'GET /studies/:id': STUDY, 'POST /studies/:id/findings/screen': { shown: [F1, F2], rejected: [] },
    'GET /studies/:id/findings': { findings: [F1, F2], rejected_count: 0 }, 'GET /patterns': LIB,
    'GET /studies/:id/network': { corridor_name: 'Crenshaw Boulevard' },
    'GET /studies/:id/findings/:fid/records': { records: RECS }, ...extra }
}

describe('Findings screen', () => {
  it('runs the screen, lists findings and traces every number in the claim to its T12 cell', async () => {
    const calls = mockApi(routes())
    renderAt('/s/s1/findings')
    expect(await screen.findByText('2 findings · 0 accepted')).toBeInTheDocument()
    expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/findings/screen'))).toBe(true)
    const nums = [...document.querySelectorAll('.claim .num')]
    expect(nums.map((n) => n.textContent)).toEqual(['12', '20', '60%', '36.2%'])
    expect(nums[3]).toHaveAttribute('title', 'From table T12, cell osm-1029~dark/reference_share_pct')
    expect(screen.getByText(/Pattern library · draft/)).toBeInTheDocument()
    expect(screen.getByText('Poor visibility or lighting')).toBeInTheDocument()
    expect(await screen.findByRole('tab', { name: 'Records (12)' })).toBeInTheDocument()
  })

  it('shows records, a collision diagram with one glyph per record, and the audit', async () => {
    mockApi(routes())
    renderAt('/s/s1/findings')
    await screen.findByRole('tab', { name: 'Records (12)' })
    expect(document.querySelectorAll('.tabbody tbody tr')).toHaveLength(12)
    fireEvent.click(screen.getByRole('tab', { name: 'Collision diagram' }))
    expect(screen.getByRole('img', { name: 'Collision diagram, 12 records, schematic' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Audit' }))
    expect(screen.getByText(/P\(true share > reference share\) = 0.97/)).toBeInTheDocument()
    expect(screen.getByText('Code, from table T12 (no AI)')).toBeInTheDocument()
  })

  it('accepts a finding and switches between findings', async () => {
    const calls = mockApi(routes({ 'PATCH /studies/:id/findings/:fid': { ...F1, status: 'accepted' } }))
    renderAt('/s/s1/findings')
    fireEvent.click(await screen.findByRole('button', { name: '✓ Accept' }))
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(await screen.findByText('2 findings · 1 accepted')).toBeInTheDocument()
    const list = screen.getByRole('complementary', { name: 'Findings list' })
    fireEvent.click(within(list).getByText(/Broadside crashes over-represented/))
    expect(await screen.findByText('F2 · Marine Avenue – West 147th Street')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Right-angle conflict/ })).toBeInTheDocument()
  })

  it('says plainly when no crash type stands out', async () => {
    mockApi(routes({ 'POST /studies/:id/findings/screen': { shown: [], rejected: [] }, 'GET /studies/:id/findings': { findings: [], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    expect(await screen.findByText('No crash type stands out')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Go to export →' })).toHaveClass('sf-btn--go')
  })

  it('marks a stale finding and blocks accepting it', async () => {
    const stale = { ...F1, stale: true, stale_reasons: ['declared 12 does not match T12/osm-1029~dark/target_crashes = 9'] }
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [stale, F2], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    expect(await screen.findByText('Stale')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('no longer matches the data')
    expect(screen.getByRole('button', { name: '✓ Accept' })).toBeDisabled()
  })
})
