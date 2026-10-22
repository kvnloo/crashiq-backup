import { describe, expect, it } from 'vitest'
import { isVru, vruHeadline, vruWho } from './vru'

const t19 = (vals) => ({ rows: Object.entries(vals).map(([key, values]) => ({ key, values })) })

describe('pedestrian, bicycle, e-bike and e-scooter words (#136, N9)', () => {
  it('names e-bikes and e-scooters in the headline only when there are some', () => {
    const base = { ped: { crashes: 12 }, bike: { crashes: 7 }, ebike: { crashes: 0 }, escooter: { crashes: 0 },
      ped_or_bike: { crashes: 19, ksi_crashes: 1, share_of_ksi_pct: 25, share_of_crashes_pct: 9.9 }, all: { ksi_crashes: 4 } }
    expect(vruHeadline(t19(base)).lead).toBe('12 pedestrian and 7 bicycle crashes: ')
    const h = vruHeadline(t19({ ...base, ebike: { crashes: 2 }, escooter: { crashes: 3 } }))
    expect(h.lead).toBe('12 pedestrian, 7 bicycle, 2 e-bike and 3 e-scooter crashes: ')
    expect(h.pct).toBe(25)
  })
  it('rings and hover words follow the crash flags', () => {
    expect(isVru({ escooter: true })).toBe(true)
    expect(isVru({ motorcycle: true })).toBe(false)
    expect(vruWho({ ped: true, ebike: true })).toBe('pedestrian and e-bike')
  })
})
