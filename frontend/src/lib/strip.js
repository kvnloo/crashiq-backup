// Strip diagram helpers (#102): short street names and label placement without overlap. Pure functions.
const CHAR = 6.6             // ~px per character at 11 px mono, for label collision checks

// "West 135th Street" -> "W 135th St": the strip is narrow, full names are on hover
export function shortName(name) {
  return String(name || '').replace(/\bNorth\b/g, 'N').replace(/\bSouth\b/g, 'S').replace(/\bEast\b/g, 'E').replace(/\bWest\b/g, 'W')
    .replace(/\bBoulevard\b/g, 'Blvd').replace(/\bAvenue\b/g, 'Av').replace(/\bStreet\b/g, 'St').replace(/\bRoad\b/g, 'Rd')
    .replace(/\bDrive\b/g, 'Dr').replace(/\bParkway\b/g, 'Pkwy').replace(/\bLane\b/g, 'Ln').replace(/\bPlace\b/g, 'Pl')
    .replace(/\bWay\b/g, 'Wy').split(' / ')[0]
}

// Greedy label placement on two rows under the line; a label that fits on neither is left to the hover title.
export function placeLabels(ticks, width) {
  const ends = [-Infinity, -Infinity]
  return ticks.map((t) => {
    const w = t.label.length * CHAR + 10
    const left = Math.max(0, Math.min(width - w, t.x - w / 2))
    const row = ends.findIndex((e) => left >= e)
    if (row === -1) return { ...t, row: null }
    ends[row] = left + w
    return { ...t, row, left, w }
  })
}
