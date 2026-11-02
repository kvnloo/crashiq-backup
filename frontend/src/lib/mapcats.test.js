import { describe, expect, it } from 'vitest'
import crashes from '../__fixtures__/crashes.json'
import network from '../__fixtures__/network.json'
import { SEVERITY } from './severity'
import { KSI_MIN, SLOTS, OTHER, catOf, categories, columns, corridorAzimuth, locationPoints, topLocations, visible } from './mapcats'

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
    expect(catOf('severity', { severity: 'B' })).toBe('B')        // #108: each KABCO level is its own category
    expect(catOf('severity', { severity: 'C' })).toBe('C')
    expect(catOf('severity', { severity: undefined })).toBe('U')
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

  it('stacks Fatal and Serious at the base, then B, C, U, PDO (#272)', () => {
    const loc = [{ id: 'x', name: 'X', lon: -118.3, lat: 33.9, kind: 'intersection' }]
    const sev = ['O', 'O', 'O', 'C', 'B', 'A', 'K', 'U'].map((s, i) => ({ crash_id: String(i), severity: s, location_id: 'x' }))
    const fc = columns(loc, sev, 'severity', categories('severity', sev), 200)
    const order = [...fc.features].sort((a, b) => a.properties.base - b.properties.base).map((f) => f.properties.key)
    expect(order).toEqual(['K', 'A', 'B', 'C', 'U', 'O'])
  })

  it('a KSI slab stays visible under a tall property-damage stack, and the column height still equals its crashes', () => {
    const loc = [{ id: 'x', name: 'X', lon: -118.3, lat: 33.9, kind: 'intersection' }]
    const sev = [{ severity: 'K' }, ...Array.from({ length: 199 }, () => ({ severity: 'O' }))]
      .map((c, i) => ({ ...c, crash_id: String(i), location_id: 'x' }))
    const fc = columns(loc, sev, 'severity', categories('severity', sev), 200)
    const k = fc.features.find((f) => f.properties.key === 'K').properties
    expect(k.top - k.base).toBeCloseTo(200 * KSI_MIN, 6)                 // 1 of 200 would be 1 m: shown at 8 m
    expect(Math.max(...fc.features.map((f) => f.properties.top))).toBeCloseTo(200, 6)
  })

  it('lays a north–south corridor across the screen', () => {
    expect(corridorAzimuth([[33.89, -118.3], [33.91, -118.3]])).toBeCloseTo(0, 6)
    expect(corridorAzimuth([[33.9, -118.31], [33.9, -118.29]])).toBeCloseTo(90, 6)
  })
})

describe('topLocations (#100)', () => {
  const locs = [{ id: 'a', name: 'A St' }, { id: 'b', name: 'B St' }, { id: 'c', name: 'C St' }, { id: 'd', name: 'D St' }, { id: 'e', name: 'E St' }]
  const cr = (id, n) => Array.from({ length: n }, () => ({ location_id: id }))
  it('keeps the five with the most crashes, ties by name, none without crashes (#272)', () => {
    expect(topLocations(locs, [...cr('c', 5), ...cr('a', 2), ...cr('b', 2), ...cr('d', 1)])).toEqual(['c', 'a', 'b', 'd'])
    expect(topLocations(locs, [...cr('c', 5), ...cr('a', 2), ...cr('b', 2), ...cr('d', 1)], 3)).toEqual(['c', 'a', 'b'])
    expect(topLocations(locs, cr('e', 1))).toEqual(['e'])
    expect(topLocations(locs, [])).toEqual([])
  })
})

describe('severity categories (#108)', () => {
  it('list K/A/B/C/O in order with the one ramp, and U only when present', () => {
    const cats = categories('severity', [{ severity: 'K' }, { severity: 'C' }])
    expect(cats.map((c) => c.key)).toEqual(['K', 'A', 'B', 'C', 'O'])
    expect(cats.map((c) => c.color)).toEqual(['K', 'A', 'B', 'C', 'O'].map((k) => SEVERITY[k]))
    expect(categories('severity', [{ severity: 'U' }]).map((c) => c.key)).toContain('U')
  })
})


describe('level not stated is hollow (#108 round 2)', () => {
  it('flags U as hollow and nothing else', () => {
    const cats = categories('severity', [{ severity: 'U' }, { severity: 'O' }])
    expect(cats.filter((c) => c.hollow).map((c) => c.key)).toEqual(['U'])
    expect(categories('type', [{ collision_type: 'BROADSIDE' }]).some((c) => c.hollow)).toBe(false)
  })
})

describe('locationPoints: segments at the study ends (#375)', () => {
  const line = [[33.8628, -118.3205], [33.8708, -118.3405], [33.8895, -118.3592]]

  it('a corridor with no intersections still gets a column for its one A–B segment', () => {
    const net = { line, intersections: [], segments: [{ id: 'seg:A:B', from_id: 'A', to_id: 'B', name: 'Study start (A) – Study end (B)' }] }
    const locs = locationPoints(net)
    expect(locs.map((l) => l.id)).toEqual(['seg:A:B'])
    expect(locs[0]).toMatchObject({ lat: (33.8628 + 33.8895) / 2, lon: (-118.3205 + -118.3592) / 2, kind: 'segment' })
    expect(columns(locs, [{ crash_id: '1', location_id: 'seg:A:B', severity: 'O' }], 'severity',
      [{ key: 'O', label: 'PDO', color: '#888' }]).features).toHaveLength(1)
  })

  it('the end segments (A to the first intersection, the last intersection to B) get columns too', () => {
    const net = { line, intersections: [{ id: 'i1', name: 'Mid St', lat: 33.8708, lon: -118.3405, is_study: true }],
      segments: [{ id: 'seg:A:i1', from_id: 'A', to_id: 'i1', name: 'A – Mid St' }, { id: 'seg:i1:B', from_id: 'i1', to_id: 'B', name: 'Mid St – B' }] }
    expect(locationPoints(net).map((l) => l.id).sort()).toEqual(['i1', 'seg:A:i1', 'seg:i1:B'])
  })

  it('without a line the end segments are still skipped, not placed at a guess', () => {
    const net = { intersections: [], segments: [{ id: 'seg:A:B', from_id: 'A', to_id: 'B' }] }
    expect(locationPoints(net)).toEqual([])
  })
})
