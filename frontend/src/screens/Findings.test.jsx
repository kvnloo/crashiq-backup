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

// the corridor summary opens first (#270); these tests read a finding, so open the first card
async function openFirst() {
  fireEvent.click((await screen.findAllByTestId('fcard'))[0])
}

describe('Findings screen', () => {
  it('runs the screen, lists findings and traces every number in the claim to its T12 cell', async () => {
    const calls = mockApi(routes())
    renderAt('/s/s1/findings')
    await openFirst()
    expect(await screen.findByText('2 findings · 0 accepted')).toBeInTheDocument()
    expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/findings/screen'))).toBe(true)
    const nums = [...document.querySelectorAll('.claim .num')]
    expect(nums.map((n) => n.textContent)).toEqual(['12', '20', '60%', '36.2%'])
    expect(nums[3]).toHaveAttribute('title', 'From table T12, cell osm-1029~dark/reference_share_pct')
    expect(screen.getByText(/Pattern library · draft/)).toBeInTheDocument()
    expect(screen.getByText('Poor visibility or lighting')).toBeInTheDocument()
    expect(await screen.findByRole('tab', { name: 'Records (12)' })).toBeInTheDocument()
  })

  it('shows records and the audit (the collision diagram is at the top now, #268)', async () => {
    mockApi(routes())
    renderAt('/s/s1/findings')
    await openFirst()
    await screen.findByRole('tab', { name: 'Records (12)' })
    expect(document.querySelectorAll('.tabbody tbody tr')).toHaveLength(12)
    expect(screen.queryByRole('tab', { name: 'Collision diagram' })).toBeNull()
    fireEvent.click(screen.getByRole('tab', { name: 'Audit' }))
    expect(screen.getByText(/P\(true share > reference share\) = 0.97/)).toBeInTheDocument()
    expect(screen.getByText('Code, from table T12 (no AI)')).toBeInTheDocument()
  })

  it('accepts a finding and switches between findings', async () => {
    const calls = mockApi(routes({ 'PATCH /studies/:id/findings/:fid': { ...F1, status: 'accepted' } }))
    renderAt('/s/s1/findings')
    await openFirst()
    fireEvent.click(await screen.findByRole('button', { name: '✓ Accept' }))
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(await screen.findByText('2 findings · 1 accepted')).toBeInTheDocument()
    const list = screen.getByRole('complementary', { name: 'Findings list' })
    fireEvent.click(within(list).getByText(/Broadside crashes over-represented/))
    expect(await screen.findByText('F2 · Marine Avenue – West 147th Street')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Play the pattern' }))             // never autoplays (#268)
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
    await openFirst()
    expect(await screen.findByText('Stale')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('no longer matches the data')
    expect(screen.getByRole('button', { name: '✓ Accept' })).toBeDisabled()
  })

  it('never says "all numbers traced" on a stale finding (#266)', async () => {
    const stale = { ...F1, stale: true, stale_reasons: ['declared 12 does not match T12/osm-1029~dark/target_crashes = 9'] }
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [stale], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    await openFirst()
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
    await openFirst()
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
    await openFirst()
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
    await openFirst()
    expect(await screen.findByText('Excessive speed · Left-turn conflicts')).toBeInTheDocument()
    expect(screen.queryByText(/No library entry/)).toBeNull()
  })

  it('a finding whose pattern key is missing still finds its library entry by its reference', async () => {
    const X = { ...K, meta: { ...K.meta, pattern: undefined } }
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [X], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    await openFirst()
    expect(await screen.findByText('Poor visibility or lighting')).toBeInTheDocument()
  })

  it('trims only a trailing " at <location>"; an untitled finding keeps its text whole', async () => {
    const T = { ...M, id: 't', title: 'Crashes with poor delineation at night over-represented at Marine Avenue – West 147th Street' }
    const U = { ...S, id: 'u', title: null, text: 'Hit object crashes from poor delineation at night.' }
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [T, U], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    await openFirst()
    const list = await screen.findByRole('complementary', { name: 'Findings list' })
    const tt = within(list).getAllByTestId('fcard').map((c) => c.querySelector('.tt').textContent)
    expect(tt).toEqual(['Crashes with poor delineation at night over-represented', 'Hit object crashes from poor delineation at night.'])
  })
})

// #268: the N10 collision diagram of the finding's own crashes at the top; the replay only on request
import FD from '../__fixtures__/finding_diagram.json'

describe('Finding collision diagram (#268)', () => {
  const fdRoutes = (extra = {}) => routes({ 'GET /studies/:id/findings': { findings: [FD.finding], rejected_count: 0 },
    'GET /studies/:id/findings/:fid/records': { records: FD.records },
    'GET /studies/:id/findings/:fid/diagram': FD.diagram, ...extra })

  it('an intersection finding opens on its N10 diagram: its records only, drawn minus not-drawn, keyed to a list', async () => {
    mockApi(fdRoutes())
    renderAt('/s/s1/findings')
    await openFirst()
    const svg = await screen.findByTestId('collision-diagram')
    const d = FD.diagram.diagram
    expect(svg).toHaveAttribute('aria-label', expect.stringContaining(`${FD.records.length} crashes`))
    const nums = [...svg.querySelectorAll('text')].map((t) => t.textContent).filter((t) => /^[\d, ]+$/.test(t))
      .flatMap((t) => t.split(','))
    expect(nums).toHaveLength(FD.records.length - Object.values(d.not_drawn).reduce((a, b) => a + b, 0))
    const list = screen.getByText('Crash list (numbers on the diagram)').closest('details')
    expect(within(list).getAllByRole('row').slice(1)).toHaveLength(FD.records.length)
  })

  it('the replay never autoplays: it is behind "Play the pattern", with no Pause or Replay buttons', async () => {
    mockApi(fdRoutes())
    renderAt('/s/s1/findings')
    await openFirst()
    await screen.findByTestId('collision-diagram')
    expect(screen.queryByRole('img', { name: /Pattern replay/ })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Play the pattern' }))
    expect(screen.getByRole('img', { name: /Pattern replay/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Pause|Replay/ })).toBeNull()
  })

  it('a segment finding shows where the segment lies on the corridor and its records, no intersection diagram', async () => {
    const seg = { ...FD.finding, id: 'seg', location_id: 'seg-1', meta: { ...FD.finding.meta, kind: 'segment' } }
    mockApi(fdRoutes({ 'GET /studies/:id/findings': { findings: [seg], rejected_count: 0 },
      'GET /studies/:id/findings/:fid/diagram': { kind: 'segment', records: FD.records.length, diagram: null,
        strip: { location_id: 'seg-1', name: 'Marine Avenue – West 147th Street', from_ft: 1000, to_ft: 3000, length_ft: 10000,
          intersections: [{ id: 'i1', name: 'Marine Avenue', station_ft: 1000 }, { id: 'i2', name: 'West 147th Street', station_ft: 3000 }],
          crashes: FD.records.map((r, i) => ({ ...r, station_ft: 1200 + 100 * i, location_id: 'seg-1' })) } } }))
    renderAt('/s/s1/findings')
    await openFirst()
    const strip = await screen.findByTestId('finding-strip')
    // PM review of #293: labelled with the segment's name and its end cross-streets; the finding's crashes as dots
    expect(within(strip).getByTestId('strip-highlight')).toHaveTextContent('Marine Avenue – West 147th Street')
    expect(within(strip).getByLabelText('Marine Avenue on the strip')).toBeInTheDocument()
    expect(within(strip).getByLabelText('West 147th Street on the strip')).toBeInTheDocument()
    expect(within(strip).getAllByTestId('strip-dot')).toHaveLength(FD.records.length)
    expect(screen.queryByTestId('collision-diagram')).toBeNull()
    expect(document.querySelectorAll('.tabbody tbody tr')).toHaveLength(FD.records.length)
  })
})

describe('Corridor summary (#270)', () => {
  const T2 = { id: 'T2', title: 'Locations', columns: [], provenance: {}, rows: [
    { key: 'osm-1', label: 'Marine Avenue', values: { crashes: 30, ksi_crashes: 2, vru_crashes: 1 } },
    { key: 'osm-1029', label: 'West 135th Street', values: { crashes: 20, ksi_crashes: 1, vru_crashes: 4 } },
    { key: 'seg-x', label: 'Marine Avenue – West 147th Street', values: { crashes: 9, ksi_crashes: 0, vru_crashes: 0 } },
    { key: 'osm-2', label: 'West 144th Street', values: { crashes: 12, ksi_crashes: 0, vru_crashes: 2 } },
    { key: 'osm-3', label: 'West 132nd Street', values: { crashes: 11, ksi_crashes: 1, vru_crashes: 0 } },
    { key: 'osm-4', label: 'West 139th Street', values: { crashes: 10, ksi_crashes: 0, vru_crashes: 0 } },
    { key: 'osm-5', label: 'Empty', values: { crashes: 0, ksi_crashes: 0, vru_crashes: 0 } }] }
  const NET = { corridor_name: 'Crenshaw Boulevard', length_ft: 6000,
    intersections: [{ id: 'osm-1029', station_ft: 2000 }], segments: [{ id: 'seg-x', from_station_ft: 4000, to_station_ft: 5000 }] }
  const F2s = { ...F2, location_id: 'seg-x', status: 'accepted' }
  const sroutes = () => routes({ 'GET /studies/:id/profile': { tables: [T2] }, 'GET /studies/:id/network': NET,
    'GET /studies/:id/findings': { findings: [F1, F2s], rejected_count: 0 } })

  it('opens first: the top locations in ranking order, each number a T2 cell, plus every location with a finding', async () => {
    mockApi(sroutes())
    renderAt('/s/s1/findings')
    const sum = await screen.findByLabelText('Corridor summary')
    expect(screen.getByTestId('fsummary')).toHaveAttribute('aria-pressed', 'true')
    const rows = within(sum).getAllByTestId('fsum-row')
    // top 5 by crashes (30, 20, 12, 11, 10), then the segment with a finding though it ranks 6th; never a 0-crash row
    expect(rows.map((r) => r.firstChild.firstChild.textContent)).toEqual(['Marine Avenue', 'West 135th Street', 'West 144th Street',
      'West 132nd Street', 'West 139th Street', 'Marine Avenue – West 147th Street'])
    ;[...T2.rows].filter((r) => r.values.crashes).sort((a, b) => b.values.crashes - a.values.crashes).slice(0, 5).forEach((r, i) => {
      expect(within(rows[i]).getByTestId('fsum-crashes')).toHaveTextContent(`${r.values.crashes} crashes`)
      expect(rows[i]).toHaveTextContent(`${r.values.ksi_crashes} KSI`)
      expect(rows[i]).toHaveTextContent(`${r.values.vru_crashes} ped/bike`)
    })
    expect(within(rows[1]).getAllByLabelText(/Source: table T2/).length).toBe(3)
    expect(rows[1]).toHaveTextContent('F1 Crashes after dark over-represented')
    expect(within(sum).getByTestId('fsum-counts')).toHaveTextContent('2 findings: 1 accepted, 1 needs review, 0 rejected.')
  })

  it('marks the finding locations F1…Fn on the strip; a marker or a location opens its first finding', async () => {
    mockApi(sroutes())
    renderAt('/s/s1/findings')
    const sum = await screen.findByLabelText('Corridor summary')
    const marks = within(sum).getAllByTestId('fmark')
    expect(marks.map((m) => m.getAttribute('aria-label'))).toEqual(['F1: West 135th Street', 'F2: Marine Avenue – West 147th Street'])
    fireEvent.click(marks[1])
    expect(await screen.findByText(/^F2 · /)).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('fsummary'))
    fireEvent.click(await screen.findByRole('button', { name: 'West 135th Street' }))
    expect(await screen.findByText(/^F1 · /)).toBeInTheDocument()
  })

  it('without T2 it says so, and still counts the findings', async () => {
    mockApi(routes())
    renderAt('/s/s1/findings')
    const sum = await screen.findByLabelText('Corridor summary')
    expect(sum).toHaveTextContent("The location table (T2) isn't available.")
    expect(within(sum).getByTestId('fsum-counts')).toHaveTextContent('2 findings: 0 accepted, 2 need review')
  })
})


describe('Fatal-crash findings (#274)', () => {
  const FK = { id: 'fatal-9001', location_id: 'osm-1029', source: 'screen', status: 'proposed',
    title: 'Fatal crash at West 135th Street',
    text: 'Fatal crash at West 135th Street on 2023-04-05: broadside, primary collision factor "22350", involving a pedestrian.',
    numbers: [{ value: 1, table_id: 'T2', cell: 'osm-1029/fatal_crashes' }],
    evidence_refs: { tables: ['T2'], records: { crash_id: '9001', location_id: 'osm-1029' } },
    meta: { kind_of_finding: 'fatal', pattern: 'fatal', location: 'West 135th Street', kind: 'intersection' },
    rank: { fatal_crashes: 1, ksi_crashes: 1, crashes: 1, location_fatal_crashes: 1 } }

  it('says no test was run, and the audit says it was written from the record', async () => {
    mockApi(routes({ 'GET /studies/:id/findings': { findings: [FK, F1], rejected_count: 0 } }))
    renderAt('/s/s1/findings')
    await openFirst()
    expect(await screen.findByTestId('fatal-note')).toHaveTextContent('no test is run')
    expect(screen.getAllByText('Fatal crash').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('tab', { name: 'Audit' }))
    expect(screen.getByText(/None: every fatal crash is listed/)).toBeInTheDocument()
    expect(screen.getByText(/from the crash record and table T2/)).toBeInTheDocument()
  })
})
