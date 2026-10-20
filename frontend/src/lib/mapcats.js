// Map "color by" dimensions and the stacked 3D columns. Pure functions, no map library.
// Colors: categorical slots 1–3 validated for the dark surface (dataviz validator: all-pairs pass); a 4th+ category
// folds to muted gray but keeps its own legend chip so it can still be filtered. Severity uses the one K/A/B/C/O ramp (lib/severity.js, #108);
// years use one sequential blue ramp (dark-mode steps, older = deeper).
export const SLOTS = ['#3987e5', '#d95926', '#199e70']
export const OTHER = '#6B7682'
const RAMP = ['#184f95', '#1c5cab', '#256abf', '#2a78d6', '#3987e5', '#5598e7', '#6da7ec', '#86b6ef', '#9ec5f4', '#b7d3f6']
import { HOLLOW, SEVERITY, SEVERITY_LABEL } from './severity'

const title = (s) => (s || '').toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase())
const isDark = (c) => (c.lighting || '').toUpperCase().startsWith('DARK')

export const DIMENSIONS = [
  { key: 'severity', label: 'Severity' },
  { key: 'type', label: 'Collision type' },
  { key: 'year', label: 'Year' },
  { key: 'tod', label: 'Time of day' },
  { key: 'light', label: 'Lighting' },
]

// Category key of one crash on one dimension.
export function catOf(dim, c) {
  if (dim === 'severity') return SEVERITY[c.severity] ? c.severity : 'U'
  if (dim === 'type') return (c.collision_type || 'NOT STATED').toUpperCase()
  if (dim === 'year') return String(c.year ?? (c.date || '').slice(0, 4) ?? '')
  if (dim === 'tod') {
    const h = c.hour
    if (h == null) return 'none'
    if ((h >= 6 && h < 9) || (h >= 15 && h < 19)) return 'peak'
    if (h >= 9 && h < 15) return 'midday'
    return 'night'
  }
  if (dim === 'light') {
    const l = (c.lighting || '').toUpperCase()
    if (!l || l.startsWith('NOT')) return 'none'
    if (isDark(c)) return l.includes('NO STREET') || l.includes('NOT FUNCTION') ? 'unlit' : 'dark'
    if (l.includes('DUSK') || l.includes('DAWN')) return 'dusk'
    return 'day'
  }
  return ''
}

// Ordered categories for a dimension over the whole dataset (fixed, so filters never repaint survivors).
export function categories(dim, crashes) {
  const n = new Map()
  for (const c of crashes) { const k = catOf(dim, c); n.set(k, (n.get(k) || 0) + 1) }
  const has = (k) => n.has(k)
  let list
  if (dim === 'severity') {
    list = ['K', 'A', 'B', 'C', 'U', 'O'].filter((k) => k !== 'U' || has(k)).map((k) => [k, SEVERITY_LABEL[k], SEVERITY[k]])
  } else if (dim === 'type') {
    const keys = [...n.keys()].sort((a, b) => n.get(b) - n.get(a) || a.localeCompare(b))
    const named = keys.filter((k) => k !== 'NOT STATED' && k !== 'OTHER')
    list = [...named, ...keys.filter((k) => !named.includes(k))].map((k, i) => [k, title(k), named.indexOf(k) > -1 && i < 3 ? SLOTS[i] : OTHER])
  } else if (dim === 'year') {
    const ys = [...n.keys()].filter(Boolean).sort()
    list = ys.map((y, i) => [y, y, RAMP[Math.round((i / Math.max(1, ys.length - 1)) * (RAMP.length - 1))]])
  } else if (dim === 'tod') {
    list = [['peak', 'Peak (6–9, 15–19)', SLOTS[0]], ['midday', 'Midday (9–15)', SLOTS[2]], ['night', 'Evening & night (19–6)', SLOTS[1]], ['none', 'Hour not stated', OTHER]]
  } else {
    list = [['day', 'Daylight', SLOTS[1]], ['dark', 'Dark, street lights', SLOTS[0]], ['unlit', 'Dark, no working lights', SLOTS[2]],
      ['dusk', 'Dusk or dawn', OTHER], ['none', 'Not stated', OTHER]]
  }
  return list.filter(([k]) => dim === 'severity' || has(k))
    .map(([key, label, color]) => ({ key, label, color, count: n.get(key) || 0, hollow: dim === 'severity' && HOLLOW.has(key) }))
}

// hidden: { [dim]: Set(keys) }. A crash shows only when no dimension hides it.
export function visible(c, hidden) {
  for (const [dim, set] of Object.entries(hidden)) if (set?.size && set.has(catOf(dim, c))) return false
  return true
}

// A ~circular footprint (n-gon) of radius r metres around [lon, lat].
export function ring(lon, lat, r = 11, n = 20) {
  const dLat = r / 111320, dLon = r / (111320 * Math.cos((lat * Math.PI) / 180))
  const pts = Array.from({ length: n }, (_, i) => {
    const a = (i / n) * Math.PI * 2
    return [lon + Math.cos(a) * dLon, lat + Math.sin(a) * dLat]
  })
  return [[...pts, pts[0]]]
}

// Stacked columns: one stack per location, one slab per category, heights in metres.
// locations: [{id, name, lon, lat, kind}]; crashes carry location_id.
export function columns(locations, crashes, dim, cats, maxHeight = 220, radius = 14) {
  const per = new Map(locations.map((l) => [l.id, []]))
  for (const c of crashes) per.get(c.location_id)?.push(c)
  const max = Math.max(1, ...[...per.values()].map((v) => v.length))
  const unit = maxHeight / max
  const gap = Math.min(1.5, unit * 0.15)
  const features = []
  for (const l of locations) {
    const list = per.get(l.id) || []
    let base = 0
    for (const cat of cats) {
      const k = list.filter((c) => catOf(dim, c) === cat.key).length
      if (!k) continue
      features.push({
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: ring(l.lon, l.lat, l.kind === 'segment' ? radius * 0.7 : radius) },
        properties: { location: l.name, kind: l.kind, cat: cat.label, color: cat.color, count: k, total: list.length,
          base: base + (base ? gap : 0), top: base + k * unit },
      })
      base += k * unit
    }
  }
  return { type: 'FeatureCollection', features }
}

// The n locations with the most crashes (ties by name): the only ones labelled all the time (#100, label clutter).
export function topLocations(locations, crashes, n = 3) {
  const count = new Map()
  for (const c of crashes) if (c.location_id) count.set(c.location_id, (count.get(c.location_id) || 0) + 1)
  return locations.filter((l) => count.get(l.id))
    .sort((a, b) => count.get(b.id) - count.get(a.id) || String(a.name).localeCompare(String(b.name)))
    .slice(0, n).map((l) => l.id)
}

// Locations with coordinates: intersections at their node, segments at the midpoint of their end intersections.
export function locationPoints(net) {
  const ints = new Map((net?.intersections || []).map((i) => [i.id, i]))
  const out = (net?.intersections || []).filter((i) => i.is_study !== false && i.lat != null)
    .map((i) => ({ id: i.id, name: i.name, lat: i.lat, lon: i.lon, kind: 'intersection' }))
  for (const s of net?.segments || []) {
    const a = ints.get(s.from_id), b = ints.get(s.to_id)
    if (a && b) out.push({ id: s.id, name: s.name, lat: (a.lat + b.lat) / 2, lon: (a.lon + b.lon) / 2, kind: 'segment' })
  }
  return out
}

// Compass bearing (deg) of the corridor from its first to last point; line is [[lat, lon], ...].
export function corridorAzimuth(line) {
  if (!line || line.length < 2) return 0
  const [a, b] = [line[0], line[line.length - 1]]
  const y = (b[1] - a[1]) * Math.cos(((a[0] + b[0]) / 2) * Math.PI / 180)
  const x = b[0] - a[0]
  return (Math.atan2(y, x) * 180) / Math.PI
}
