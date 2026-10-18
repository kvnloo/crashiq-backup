import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { META, mockApi, renderAt } from '../test-utils'

// Leaflet doesn't run in jsdom: stand in a stub map that exposes the same callbacks as buttons.
vi.mock('../components/CorridorMap', () => ({
  default: (p) => (
    <div data-testid="map" data-mode={p.mode}>
      <button type="button" onClick={() => p.onAddPoint([33.8953, -118.32662])}>map: click A</button>
      <button type="button" onClick={() => p.onAddPoint([33.9123, -118.32662])}>map: click B</button>
      <button type="button" onClick={() => p.onAddIntersection([33.906, -118.32662])}>map: add here</button>
    </div>
  ),
}))

const STUDY = { id: 's1', name: 'Crenshaw', mode: 'profile', from_year: 2021, to_year: 2025, radius_ft: 250, buffer_ft: 100 }
const INTS = [
  { id: 'osm-1', name: 'Marine Avenue', station_ft: 0, lat: 33.8953, lon: -118.32662, control: 'signal', is_study: true, provenance: 'auto' },
  { id: 'osm-2', name: 'West 147th Street', station_ft: 912, lat: 33.8978, lon: -118.32662, control: 'stop', is_study: true, provenance: 'auto' },
  { id: 'osm-3', name: 'West 144th Street', station_ft: 1680, lat: 33.8999, lon: -118.32662, control: 'unknown', is_study: true, provenance: 'auto' },
]
const SEGS = [
  { id: 'seg:osm-1:osm-2', from_id: 'osm-1', to_id: 'osm-2', name: 'Marine Avenue – West 147th Street', length_ft: 912, length_mi: 0.1727, aadt: null },
  { id: 'seg:osm-2:osm-3', from_id: 'osm-2', to_id: 'osm-3', name: 'West 147th Street – West 144th Street', length_ft: 768, length_mi: 0.1455, aadt: null },
]
const NET = { line: [[33.8953, -118.32662], [33.8999, -118.32662]], length_ft: 1680, length_mi: 0.3182,
  corridor_name: 'Crenshaw Boulevard', intersections: INTS, segments: SEGS, radius_ft: 250, buffer_ft: 100, buffer_ring: [] }
const EMPTY = { line: null, intersections: [], segments: [], radius_ft: 250, buffer_ft: 100, buffer_ring: null }

describe('Corridor screen', () => {
  it('starts in drawing mode with no tool to turn drawing on, and finds intersections after two clicks', async () => {
    const calls = mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': STUDY, 'GET /studies/:id/network': EMPTY,
      'PUT /studies/:id/corridor': NET })
    renderAt('/s/s1/corridor')
    expect(await screen.findByTestId('map')).toHaveAttribute('data-mode', 'draw')
    expect(screen.queryByRole('button', { name: /corridor tool|intersections only/i })).toBeNull()
    const find = screen.getByRole('button', { name: 'Find intersections →' })
    expect(find).toBeDisabled()
    fireEvent.click(screen.getByText('map: click A'))
    fireEvent.click(screen.getByText('map: click B'))
    expect(screen.getByRole('button', { name: 'Clear line' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Find intersections →' }))
    await screen.findByText('West 147th Street')
    const put = calls.find((c) => c.method === 'PUT')
    expect(put.body.line).toEqual([[33.8953, -118.32662], [33.9123, -118.32662]])
    expect(screen.getByRole('button', { name: 'Build the profile →' })).toBeInTheDocument()
  })

  it('lists locations in corridor order with segments between and one green primary', async () => {
    mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': STUDY, 'GET /studies/:id/network': NET })
    renderAt('/s/s1/corridor')
    await screen.findByRole('button', { name: 'Marine Avenue' })
    await waitFor(() => expect(screen.getByLabelText(/influence radius/i)).toBeInTheDocument())
    const panel = screen.getByRole('complementary', { name: 'Corridor locations' })
    const names = within(panel).getAllByRole('listitem').map((li) => li.textContent)
    expect(names[0]).toContain('Marine Avenue')
    expect(names[1]).toContain('West 147th Street')
    expect(within(panel).getByText('0.17 mi')).toBeInTheDocument()
    expect(within(panel).getByText('Signal')).toBeInTheDocument()
    expect(panel.querySelectorAll('.sf-btn--go')).toHaveLength(1)
  })

  it('renames, unflags, removes and adds intersections through the API', async () => {
    const calls = mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': STUDY, 'GET /studies/:id/network': NET,
      'PATCH /studies/:id/intersections/:iid': NET, 'DELETE /studies/:id/intersections/:iid': NET,
      'POST /studies/:id/intersections': NET })
    renderAt('/s/s1/corridor')
    fireEvent.click(await screen.findByRole('button', { name: 'West 144th Street' }))
    const input = screen.getByLabelText('Rename West 144th Street')
    fireEvent.change(input, { target: { value: '144th St' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH' && c.body.name === '144th St')).toBe(true))

    fireEvent.click(screen.getByLabelText('Study intersection: West 147th Street'))
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH' && c.body.is_study === false)).toBe(true))

    fireEvent.click(screen.getByLabelText('Remove Marine Avenue'))
    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE' && c.path.endsWith('/osm-1'))).toBe(true))

    fireEvent.click(screen.getByRole('button', { name: '+ Add intersection' }))
    expect(screen.getByTestId('map')).toHaveAttribute('data-mode', 'add')
    fireEvent.click(screen.getByText('map: add here'))
    await waitFor(() => expect(calls.some((c) => c.method === 'POST' && c.body.lat === 33.906)).toBe(true))
  })

  it('keeps radius, buffer and AADT behind a closed "More options" with HSM defaults', async () => {
    const calls = mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': STUDY, 'GET /studies/:id/network': NET,
      'PATCH /studies/:id/segments/:sid': NET, 'PATCH /studies/:id': STUDY })
    renderAt('/s/s1/corridor')
    const details = (await screen.findByText('More options')).closest('details')
    expect(details.open).toBe(false)
    expect(screen.getByLabelText(/influence radius/i)).toHaveValue('250')
    expect(screen.getByLabelText(/Corridor buffer/)).toHaveValue(100)
    expect(screen.queryByLabelText(/Segment AADT/)).toBeNull()
    fireEvent.click(screen.getByLabelText('Enter AADT to compute rates'))
    const seg = screen.getByLabelText('Segment AADT, Marine Avenue – West 147th Street')
    fireEvent.change(seg, { target: { value: '32000' } })
    fireEvent.blur(seg)
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH' && c.body.aadt === 32000)).toBe(true))
    expect(screen.getAllByLabelText(/approach AADT/)).toHaveLength(6)
  })

  it('starts from the corridor line in an imported project context', async () => {
    const calls = mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': STUDY, 'GET /studies/:id/network': EMPTY,
      'GET /studies/:id/context/prefill': { prefill: { line: [[33.8953, -118.32662], [33.9123, -118.32662]] } },
      'PUT /studies/:id/corridor': NET })
    renderAt('/s/s1/corridor')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Find intersections →' })).toBeEnabled())
    expect(screen.getByTestId('map')).toHaveAttribute('data-mode', 'review')
    fireEvent.click(screen.getByRole('button', { name: 'Find intersections →' }))
    await waitFor(() => expect(calls.find((c) => c.method === 'PUT')?.body.line).toHaveLength(2))
  })
})
