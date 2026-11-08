// Pedestrians, bicyclists, e-bikes and e-scooters (#136, N9 #169): words around T19 cells; no number is computed here.
import { fmt } from './tables'

// who is involved, for the ring marker and its hover text (crash flags from the pull)
export const ROAD_USER_WORDS = [['ped', 'pedestrian'], ['bike', 'bicyclist'], ['ebike', 'e-bike'], ['escooter', 'e-scooter']]
export const isVru = (c) => ROAD_USER_WORDS.some(([k]) => c[k])
export const vruWho = (c) => {
  const w = ROAD_USER_WORDS.filter(([k]) => c[k]).map(([, word]) => word)
  return w.length > 1 ? `${w.slice(0, -1).join(', ')} and ${w[w.length - 1]}` : w[0] || ''
}
export const RING_LEGEND = 'Ring: pedestrian, bicyclist, e-bike or e-scooter involved'

// min: the server's small-number threshold (#271): a share of fewer KSI crashes than this is said as counts only
// fatalOnly (#19): the state's data has no injury levels (NY), so KSI is fatal only and is said that way
export function vruHeadline(t19, min = 0, fatalOnly = false) {
  const ksiWords = fatalOnly ? 'killed someone (no injury levels in this data)' : 'killed or seriously injured someone'
  const v = (k) => t19.rows.find((r) => r.key === k)?.values || {}
  const ped = v('ped').crashes || 0, bike = v('bike').crashes || 0, both = v('ped_or_bike'), all = v('all')
  const e = (v('ebike').crashes || 0) + (v('escooter').crashes || 0)
  const parts = [`${fmt(ped)} pedestrian`, `${fmt(bike)} bicycle`]
  if (v('ebike').crashes) parts.push(`${fmt(v('ebike').crashes)} e-bike`)
  if (v('escooter').crashes) parts.push(`${fmt(v('escooter').crashes)} e-scooter`)
  const crashes = `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]} crash${ped + bike + e === 1 ? '' : 'es'}`
  if (!both.crashes) return { lead: 'No pedestrian, bicycle, e-bike or e-scooter crashes in this window.', rest: '' }
  if (!all.ksi_crashes) return { lead: `${crashes}.`, rest: fatalOnly ? ' No crash on the corridor killed anyone.' : ' No crash on the corridor killed or seriously injured anyone.' }
  const ofAll = all.crashes < min ? '' : `, and ${fmt(both.share_of_crashes_pct)}% of all crashes`
  if (all.ksi_crashes < min) {
    return { lead: `${crashes}: `, rest: `${fmt(both.ksi_crashes)} of the ${fmt(all.ksi_crashes)} crashes that ${ksiWords} (too few to compare as a share)${ofAll}.` }
  }
  return { lead: `${crashes}: `, pct: both.share_of_ksi_pct,
    rest: ` of all crashes that ${ksiWords} (${fmt(both.ksi_crashes)} of ${fmt(all.ksi_crashes)})${ofAll}.` }
}
