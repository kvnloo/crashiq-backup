import { describe, expect, it } from 'vitest'
import { locationPoints } from './locationPoints'

const net = {
  line: [[37.58, -122.08], [37.57, -122.07]],
  intersections: [{ id: 'osm-1', lat: 37.578, lon: -122.079 }, { id: 'osm-2', lat: 37.575, lon: -122.078 }],
}

describe('locationPoints', () => {
  it('puts intersections at their node and segments halfway between their ends, values from T2', () => {
    const rows = [
      { key: 'osm-1', label: 'Dyer St', values: { crashes: 11, injury_crashes: 4, ksi_crashes: 1 } },
      { key: 'seg:osm-1:osm-2', label: 'Dyer – Rose', values: { crashes: 2, injury_crashes: 0, ksi_crashes: 0 } },
      { key: 'seg:A:osm-1', label: 'Start – Dyer', values: { crashes: 1, injury_crashes: 1, ksi_crashes: 0 } },
      { key: 'osm-2', label: 'Rose Wy', values: { crashes: 0, injury_crashes: 0, ksi_crashes: 0 } },
    ]
    const pts = locationPoints(rows, net)
    expect(pts.map((p) => p.key)).toEqual(['osm-1', 'seg:osm-1:osm-2', 'seg:A:osm-1'])   // zero-crash rows dropped
    expect(pts[0]).toMatchObject({ pos: [-122.079, 37.578], crashes: 11, injury: 4, ksi: 1, seg: false })
    expect(pts[1].pos[0]).toBeCloseTo(-122.0785) && expect(pts[1].seg).toBe(true)
    expect(pts[2].pos[1]).toBeCloseTo((37.58 + 37.578) / 2)
  })

  it('skips locations it cannot position', () => {
    expect(locationPoints([{ key: 'osm-9', values: { crashes: 3 } }], net)).toEqual([])
  })
})
