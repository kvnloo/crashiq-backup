import { describe, expect, it } from 'vitest'
import { roadsText } from './roads'

describe('roadsText', () => {
  it('adds where a house-address crash happened (#397)', () => {
    const c = { primary_road: '440 W MANCHESTER BLVD (PARKING LOT)', secondary_road: 'PRIVATE PROPERTY',
      location_label: 'in front of 440 W MANCHESTER BLVD' }
    expect(roadsText(c)).toBe('440 W MANCHESTER BLVD (PARKING LOT) / PRIVATE PROPERTY (in front of 440 W MANCHESTER BLVD)')
  })
  it('is the two road fields otherwise', () => {
    expect(roadsText({ primary_road: 'CRENSHAW BL', secondary_road: 'W 144TH ST' })).toBe('CRENSHAW BL / W 144TH ST')
    expect(roadsText({ primary_road: 'CRENSHAW BL' }, '—')).toBe('CRENSHAW BL / —')
  })
})
