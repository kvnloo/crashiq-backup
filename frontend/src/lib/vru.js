// Pedestrians and bicyclists headline (#136): words around T19 cells; no number is computed here.
import { fmt } from './tables'

export function vruHeadline(t19) {
  const v = (k) => t19.rows.find((r) => r.key === k)?.values || {}
  const ped = v('ped').crashes || 0, bike = v('bike').crashes || 0, both = v('ped_or_bike'), all = v('all')
  const crashes = `${fmt(ped)} pedestrian and ${fmt(bike)} bicycle crash${ped + bike === 1 ? '' : 'es'}`
  if (!both.crashes) return { lead: 'No pedestrian or bicycle crashes in this window.', rest: '' }
  if (!all.ksi_crashes) return { lead: `${crashes}.`, rest: ' No crash on the corridor killed or seriously injured anyone.' }
  return { lead: `${crashes}: `, pct: both.share_of_ksi_pct,
    rest: ` of all crashes that killed or seriously injured someone (${fmt(both.ksi_crashes)} of ${fmt(all.ksi_crashes)}), and ${fmt(both.share_of_crashes_pct)}% of all crashes.` }
}
