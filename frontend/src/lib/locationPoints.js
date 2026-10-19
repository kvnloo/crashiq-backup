// Where each T2 location sits: intersections at their node, segments halfway between their two ends.
export function locationPoints(rows, net) {
  const ints = Object.fromEntries((net?.intersections || []).map((i) => [i.id, [i.lon, i.lat]]))
  const line = net?.line || []
  const ends = { A: line[0] && [line[0][1], line[0][0]], B: line.length && [line[line.length - 1][1], line[line.length - 1][0]] }
  const at = (id) => ints[id] || ends[id]
  return (rows || []).map((r) => {
    let pos = null
    if (r.key.startsWith('seg:')) {
      const [, a, b] = r.key.split(':')
      if (at(a) && at(b)) pos = [(at(a)[0] + at(b)[0]) / 2, (at(a)[1] + at(b)[1]) / 2]
    } else pos = at(r.key)
    return pos && { key: r.key, label: r.label || r.key, seg: r.key.startsWith('seg:'), pos,
      crashes: r.values?.crashes || 0, injury: r.values?.injury_crashes || 0, ksi: r.values?.ksi_crashes || 0 }
  }).filter((x) => x && x.crashes > 0)
}
