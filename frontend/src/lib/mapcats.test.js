import { describe, expect, it } from 'vitest'
import crashes from '../__fixtures__/crashes.json'
import network from '../__fixtures__/network.json'
import { SLOTS, OTHER, catOf, categories, columns, corridorAzimuth, locationPoints, visible } from './mapcats'

const C = crashes.crashes.filter((c) => c.lat != null)

describe('map categories', () => {
  it('covers every crash exactly once on every dimension', () => {
    for (const dim of ['severity', 'type', 'year', 'tod', 'light']) {
      const cats = categories(dim, C)
      const keys = new Set(cats.map((c) => c.key))
      expect(C.every((c) => keys.has(catOf(dim, c)))).toBe(true)
      expect(cats.reduce((a, c) => a + c.count, 0)).toBe(C.length)
    }
  })

  it('colors at most three collision types, the rest muted, in a fixed order by count', () => {
    const cats = categories('type', C)
    expect(cats.slice(0, 3).map((c) => c.color)).toEqual(SLOTS)
    expect(cats.slice(3).every((c) => c.color === OTHER)).toBe(true)
    expect(cats[0].count).toBeGreaterThanOrEqual(cats[1].count)
  })

  it('bins time of day and lighting', () => {
    expect(catOf('tod', { hour: 7 })).toBe('peak')
    expect(catOf('tod', { hour: 17 })).toBe('peak')
    expect(catOf('tod', { hour: 12 })).toBe('midday')
    expect(catOf('tod', { hour: 23 })).toBe('night')
    expect(catOf('tod', { hour: null })).toBe('none')
    expect(catOf('light', { lighting: 'DARK - STREET LIGHTS' })).toBe('dark')
    expect(catOf('light', { lighting: 'DARK - NO STREET LIGHTS' })).toBe('unlit')
    expect(catOf('light', { lighting: 'DUSK - DAWN' })).toBe('dusk')
    expect(catOf('light', { lighting: 'DAYLIGHT' })).toBe('day')
    expect(catOf('severity', { severity: 'B' })).toBe('I')
  })

  it('filters combine across dimensions', () => {
    const c = { severity: 'O', hour: 22, lighting: 'DARK - STREET LIGHTS' }
    expect(visible(c, {})).toBe(true)
    expect(visible(c, { severity: new Set(['O']) })).toBe(false)
    expect(visible(c, { severity: new Set(['K']), light: new Set(['day']) })).toBe(true)
  })
})

describe('3D columns', () => {
  const locs = locationPoints(network)
  const at = new Map(locs.map((l) => [l.id, l]))

  it('places intersections at their node and segments between their ends', () => {
    const seg = locs.find((l) => l.kind === 'segment')
    const s = network.segments.find((x) => x.id === seg.id)
    const ints = network.intersections
    const a = ints.find((i) => i.id === s.from_id), b = ints.find((i) => i.id === s.to_id)
    expect(seg.lat).toBeCloseTo((a.lat + b.lat) / 2, 9)
    expect(at.size).toBe(locs.length)
  })

  it('stacks one slab per category; the stack height is proportional to crashes at the location', () => {
    const ids = locs.map((l) => l.id)
    const placed = C.map((c, i) => ({ ...c, location_id: ids[i % 3] }))
    const cats = categories('severity', placed)
    const fc = columns(locs, placed, 'severity', cats, 200)
    const byLoc = {}
    for (const f of fc.features) {
      const p = f.properties
      expect(p.top).toBeGreaterThan(p.base)
      byLoc[p.location] = Math.max(byLoc[p.location] || 0, p.top)
      expect(f.geometry.coordinates[0][0]).toEqual(f.geometry.coordinates[0].at(-1))     // closed ring
    }
    const counts = ids.slice(0, 3).map((id) => placed.filter((c) => c.location_id === id).length)
    const tallest = Math.max(...counts)
    ids.slice(0, 3).forEach((id, i) => expect(byLoc[at.get(id).name]).toBeCloseTo((200 * counts[i]) / tallest, 6))
  })

  it('lays a north–south corridor across the screen', () => {
    expect(corridorAzimuth([[33.89, -118.3], [33.91, -118.3]])).toBeCloseTo(0, 6)
    expect(corridorAzimuth([[33.9, -118.31], [33.9, -118.29]])).toBeCloseTo(90, 6)
  })
})
