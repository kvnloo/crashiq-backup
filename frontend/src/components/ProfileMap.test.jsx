import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import crashes from '../__fixtures__/crashes.json'
import network from '../__fixtures__/network.json'
import { locationPoints } from '../lib/mapcats'

const calls = []
vi.mock('maplibre-gl', () => {
  class Map {
    constructor(o) { this.o = o; this.bearing = o.bearing || 0; this.handlers = {}; this.sources = {}; calls.push(['new', o]) }
    on(ev, a, b) { const fn = b || a; (this.handlers[ev] ||= []).push(fn); if (ev === 'load') setTimeout(() => fn(), 0) }
    getSource(id) { return (this.sources[id] ||= { setData: (d) => { this.sources[id].data = d; calls.push(['data', id, d]) } }) }
    cameraForBounds() { return { center: [-118.3, 33.9], zoom: 15 } }
    jumpTo(o) { calls.push(['jump', o]) }
    easeTo(o) { calls.push(['ease', o]); if (o.bearing != null) { this.bearing = o.bearing; (this.handlers.rotate || []).forEach((f) => f()) } }
    getBearing() { return this.bearing }
    getCanvas() { return { style: {} } }
    remove() {}
  }
  class Popup { setLngLat() { return this } setHTML() { return this } addTo() { return this } remove() {} }
  class Marker { constructor() { calls.push(['marker']) } setLngLat() { return this } addTo() { return this } remove() {} }
  return { default: { Map, Popup, Marker } }
})
vi.mock('maplibre-gl/dist/maplibre-gl.css', () => ({}))

const { default: ProfileMap } = await import('./ProfileMap')
const C = crashes.crashes.filter((c) => c.lat != null).map((c, i) => ({ ...c, location_id: network.intersections[i % 3].id }))
const last = (kind, id) => [...calls].reverse().find((c) => c[0] === kind && (!id || c[1] === id))

describe('ProfileMap', () => {
  beforeEach(() => { calls.length = 0 })

  it('opens in 3D with the corridor laid across the screen, and draws columns', async () => {
    render(<ProfileMap line={network.line} crashes={C} locations={locationPoints(network)} />)
    await screen.findByText(`Showing ${C.length} of ${C.length} crashes · column height = crashes at the location`)
    await waitFor(() => expect(last('jump')).toBeTruthy())
    expect(last('jump')[1].pitch).toBe(55)
    expect(last('jump')[1].bearing).toBe(-45)                       // north–south corridor → shown on the diagonal
    expect(last('data', 'columns')[2].features.length).toBeGreaterThan(0)
  })

  it('rotates, resets north, fits and switches to 2D', async () => {
    render(<ProfileMap line={network.line} crashes={C} locations={locationPoints(network)} />)
    await screen.findByText(/Showing/)
    fireEvent.click(screen.getByRole('button', { name: 'Rotate right' }))
    expect(last('ease')[1].bearing).toBe(45)
    fireEvent.click(screen.getByRole('button', { name: /Reset north/ }))
    expect(last('ease')[1].bearing).toBe(0)
    fireEvent.click(screen.getByRole('button', { name: 'Fit' }))
    expect(last('ease')[1]).toMatchObject({ bearing: -45, pitch: 55 })
    fireEvent.click(screen.getByRole('button', { name: '3D' }))
    expect(last('ease')[1].pitch).toBe(0)
    expect(screen.getByRole('button', { name: '2D' })).toBeInTheDocument()
    expect(last('data', 'columns')[2].features).toHaveLength(0)
  })

  it('colors by another dimension and filters with the legend chips', async () => {
    render(<ProfileMap line={network.line} crashes={C} locations={locationPoints(network)} />)
    await screen.findByText(/Showing/)
    fireEvent.click(screen.getByRole('radio', { name: 'Lighting' }))
    const legend = screen.getByLabelText('Map legend and filters')
    const dark = within(legend).getByRole('button', { name: /^Dark, street lights/ })
    const nDark = C.filter((c) => { const l = (c.lighting || '').toUpperCase(); return l.startsWith('DARK') && !l.includes('NO STREET') && !l.includes('NOT FUNCTION') }).length
    fireEvent.click(dark)
    expect(dark).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByText(new RegExp(`Showing ${C.length - nDark} of ${C.length}`))).toBeInTheDocument()
    expect(last('data', 'crashes')[2].features).toHaveLength(C.length - nDark)
    fireEvent.click(screen.getByRole('radio', { name: 'Year' }))                 // filters persist across dimensions
    expect(screen.getByText(new RegExp(`Showing ${C.length - nDark} of`))).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear 1 filter' }))
    expect(screen.getByText(new RegExp(`Showing ${C.length} of`))).toBeInTheDocument()
  })
})
