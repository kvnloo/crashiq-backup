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

  it('never says "all numbers traced" on a stale finding (#266)', async () => {
    const stale = { ...F1, stale: true, stale_reasons: ['declared 12 does not match T12/osm-1029~dark/target_crashes = 9'] }
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [stale], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    expect(await screen.findByText('Stale')).toBeInTheDocument()
    expect(screen.queryByText(/all numbers traced/)).toBeNull()
    expect(screen.getByText('validator: out of date')).toBeInTheDocument()
  })
})

describe('Findings list (#267)', () => {
  const K = { ...F1, id: 'k', location_name: 'West 135th Street', rank: { fatal_crashes: 1, ksi_crashes: 2, crashes: 12 },
    meta: { ...F1.meta, location: 'SEG:OSM-1029:OSM-1035' } }
  const M = { ...F2, id: 'm', location_name: 'Marine Avenue – West 147th Street', rank: { fatal_crashes: 0, ksi_crashes: 0, crashes: 12 } }
  const S = { ...F1, id: 's', stale: true, stale_reasons: ['x'], location_name: 'West 132nd Street', title: 'Old claim at West 132nd Street',
    rank: { fatal_crashes: 0, ksi_crashes: 0, crashes: 0 } }

  it('keeps the order the server ranks (fatal, KSI, strength, crashes), stale ones under "Out of date"', async () => {
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [K, M, S], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    const list = await screen.findByRole('complementary', { name: 'Findings list' })
    const cards = within(list).getAllByTestId('fcard')
    expect(cards.map((c) => c.querySelector('.loc-l').textContent)).toEqual(['West 135th Street', 'Marine Avenue – West 147th Street', 'West 132nd Street'])
    const sep = within(list).getByRole('separator')
    expect(sep).toHaveTextContent('Out of date')
    expect(sep.compareDocumentPosition(cards[2]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(sep.compareDocumentPosition(cards[1]) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy()
    expect(within(cards[0]).getByText('Fatal crash')).toBeInTheDocument()
  })

  it('cards are one line: location, title without the repeated location, chips; never the paragraph or an id', async () => {
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [K, M], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    const list = await screen.findByRole('complementary', { name: 'Findings list' })
    const card = within(list).getAllByTestId('fcard')[0]
    expect(card.querySelector('.tt').textContent).toBe('Crashes after dark over-represented')
    expect(list).not.toHaveTextContent(K.text)
    expect(document.body.textContent).not.toMatch(/SEG:|INT:|osm-\d/i)
    expect(screen.getByText('F1 · West 135th Street')).toBeInTheDocument()
  })

  it('a finding with its own factors but no library entry shows them, not "No library entry"', async () => {
    const X = { ...K, pattern_ref: null, meta: { ...K.meta, pattern: 'ksi', factors: ['Excessive speed', 'Left-turn conflicts'] } }
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [X], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    expect(await screen.findByText('Excessive speed · Left-turn conflicts')).toBeInTheDocument()
    expect(screen.queryByText(/No library entry/)).toBeNull()
  })

  it('a finding whose pattern key is missing still finds its library entry by its reference', async () => {
    const X = { ...K, meta: { ...K.meta, pattern: undefined } }
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [X], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    expect(await screen.findByText('Poor visibility or lighting')).toBeInTheDocument()
  })

  it('trims only a trailing " at <location>"; an untitled finding keeps its text whole', async () => {
    const T = { ...M, id: 't', title: 'Crashes with poor delineation at night over-represented at Marine Avenue – West 147th Street' }
    const U = { ...S, id: 'u', title: null, text: 'Hit object crashes from poor delineation at night.' }
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [T, U], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    const list = await screen.findByRole('complementary', { name: 'Findings list' })
    const tt = within(list).getAllByTestId('fcard').map((c) => c.querySelector('.tt').textContent)
    expect(tt).toEqual(['Crashes with poor delineation at night over-represented', 'Hit object crashes from poor delineation at night.'])
  })
})
