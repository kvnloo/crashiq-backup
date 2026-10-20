import { describe, expect, it } from 'vitest'
import network from '../__fixtures__/network.json'
import { placeLabels, shortName } from './strip'

// a dense real-world case: Union City Blvd, 10 study intersections incl. two-name corners (#36)
const UNION = ['Dyer Street', 'Rose Way', 'Bay Colony Way', 'Delores Drive', 'Rocklin Drive', 'Eastin Drive / Lowry Road',
  'Unnamed road', 'Unnamed road', 'Rancho Drive', 'Paseo Padre Parkway']
const STATIONS = [0, 978, 2121, 2751, 3300, 5300, 6000, 6349, 7440, 8295]

function overlaps(placed) {
  const rows = [0, 1].map((r) => placed.filter((t) => t.row === r).sort((a, b) => a.left - b.left))
  return rows.some((row) => row.some((t, i) => i > 0 && t.left < row[i - 1].left + row[i - 1].w))
}

describe('strip diagram labels (#102)', () => {
  it('shortens names and keeps the first of a two-name corner', () => {
    expect(shortName('West 135th Street')).toBe('W 135th St')
    expect(shortName('Eastin Drive / Lowry Road')).toBe('Eastin Dr')
    expect(shortName('Paseo Padre Parkway')).toBe('Paseo Padre Pkwy')
  })

  for (const width of [400, 600, 768, 1440]) {     // the data column is 400 px and up
    it(`never overlaps labels at ${width} px`, () => {
      for (const [names, st, len] of [[UNION, STATIONS, 8418],
        [network.intersections.map((i) => i.name), network.intersections.map((i) => i.station_ft), network.length_ft]]) {
        const ticks = names.map((n, i) => ({ id: String(i), name: n, label: shortName(n), x: 14 + (st[i] / len) * (width - 28) }))
        const placed = placeLabels(ticks, width)
        expect(overlaps(placed)).toBe(false)
        expect(placed.every((t) => t.row == null || (t.left >= 0 && t.left + t.w <= width))).toBe(true)
      }
    })
  }
})
