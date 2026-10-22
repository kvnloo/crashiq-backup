// A. Corridor strip diagram (#102): the corridor as a straight line from A to B, true to scale by station; each placed
// crash is a dot stacked at its station, colored like the map. Stations come from the assignment API; this component
// only draws them (no statistics computed here). Dot hit targets are larger than the dots; a location click opens
// the existing drill-down.
import { useEffect, useMemo, useRef, useState } from 'react'
import { categories, catOf } from '../lib/mapcats'
import { placeLabels, shortName } from '../lib/strip'
import { RING_LEGEND, isVru, vruWho } from '../lib/vru'

const R = 4                  // dot radius (8 px marker)
const STEP = 2 * R + 2       // one dot plus a 2 px surface gap
const MAX_STACK = 24         // taller stacks end in a "+n" count; the exact numbers are in the table
const PAD = 18
const RANK = { K: 0, A: 1, B: 2, C: 3, U: 4, O: 5 }
const SEV = { K: 'Fatal', A: 'Serious injury', B: 'Minor injury', C: 'Possible injury', U: 'Injury, level not stated', O: 'Property damage' }
const DIMS = [['severity', 'Severity'], ['collision_type', 'Collision type']]

export default function StripDiagram({ crashes, intersections, lengthFt, onOpen }) {
  const box = useRef(null)
  const [width, setWidth] = useState(520)
  const [dim, setDim] = useState('severity')
  const [hover, setHover] = useState(null)

  useEffect(() => {
    if (!box.current || typeof ResizeObserver === 'undefined') return undefined
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(280, Math.round(e.contentRect.width))))
    ro.observe(box.current)
    return () => ro.disconnect()
  }, [])

  const cats = useMemo(() => categories(dim, crashes), [dim, crashes])
  const color = useMemo(() => new Map(cats.map((c) => [c.key, c.color])), [cats])
  const hollow = useMemo(() => new Set(cats.filter((c) => c.hollow).map((c) => c.key)), [cats])
  const x = (st) => PAD + (Math.max(0, Math.min(lengthFt, st)) / (lengthFt || 1)) * (width - 2 * PAD)

  // dots: one column per STEP px of corridor; most severe at the bottom of each stack
  const { dots, extra, tall } = useMemo(() => {
    const bins = new Map()
    for (const c of crashes) {
      if (c.station_ft == null) continue
      const b = Math.round(x(c.station_ft) / STEP)
      if (!bins.has(b)) bins.set(b, [])
      bins.get(b).push(c)
    }
    const out = [], more = []
    let top = 0
    const at = (b) => Math.min(width - PAD, Math.max(PAD, b * STEP))   // snapped to the grid, but never past A or B
    for (const [b, list] of bins) {
      list.sort((p, q) => (RANK[p.severity] ?? 9) - (RANK[q.severity] ?? 9) || String(p.date).localeCompare(String(q.date)))
      list.slice(0, MAX_STACK).forEach((c, i) => out.push({ c, cx: at(b), i }))
      if (list.length > MAX_STACK) more.push({ cx: at(b), n: list.length - MAX_STACK })
      top = Math.max(top, Math.min(list.length, MAX_STACK))
    }
    return { dots: out, extra: more, tall: top }
  }, [crashes, width, lengthFt]) // eslint-disable-line react-hooks/exhaustive-deps

  const ticks = useMemo(() => placeLabels([...intersections].sort((a, b) => a.station_ft - b.station_ft)
    .map((i) => ({ id: i.id, name: i.name, label: shortName(i.name), x: x(i.station_ft) })), width),
  [intersections, width, lengthFt]) // eslint-disable-line react-hooks/exhaustive-deps

  const base = 20 + tall * STEP + (extra.length ? 14 : 0)     // the corridor line
  const height = base + 44

  return (
    <div className="strip" ref={box}>
      <div className="seg strip-dim" role="radiogroup" aria-label="Color dots by">
        {DIMS.map(([k, label]) => (
          <button key={k} type="button" role="radio" aria-checked={dim === k} className={dim === k ? 'on' : ''} onClick={() => setDim(k)}>{label}</button>
        ))}
      </div>
      <svg width={width} height={height} role="img" aria-label={`Crashes along the corridor from A to B: ${dots.length} dots`}>
        <line x1={PAD} x2={width - PAD} y1={base} y2={base} className="strip-line" />
        <text x={PAD - 4} y={base + 4} className="strip-end" textAnchor="end">A</text>
        <text x={width - PAD + 4} y={base + 4} className="strip-end">B</text>
        {ticks.map((t) => (
          <g key={t.id} className="strip-tick" onClick={() => onOpen?.(t.id)} role="button" aria-label={`${t.name} on the strip`}>
            <title>{t.name}</title>
            <line x1={t.x} x2={t.x} y1={base - 5} y2={base + 5} />
            <rect x={t.x - 8} y={base - 8} width={16} height={t.row === 1 ? 44 : 30} className="hit" />
            {t.row != null ? <text x={t.left + 5} y={base + 18 + t.row * 15}>{t.label}</text> : null}
          </g>
        ))}
        {dots.map(({ c, cx, i }) => {
          const cy = base - R - 3 - i * STEP
          return (
            <g key={c.crash_id} className="strip-dot" onMouseEnter={() => setHover({ c, cx, cy })} onMouseLeave={() => setHover(null)}
              onClick={() => onOpen?.(c.location_id)} data-testid="strip-dot" data-location={c.location_id}>
              <circle cx={cx} cy={cy} r={R + 3} className="hit" />
              {isVru(c) ? <circle cx={cx} cy={cy} r={R + 0.75} className="vru-ring" data-testid="strip-vru" /> : null}
              {dim === 'severity' && hollow.has(catOf(dim, c))
                ? <circle cx={cx} cy={cy} r={R - 0.5} fill="none" stroke={color.get(catOf(dim, c))} strokeWidth={1.5} className="hollow" />
                : <circle cx={cx} cy={cy} r={isVru(c) ? R - 0.75 : c.severity === 'K' || c.severity === 'A' ? R + 1 : R} fill={color.get(catOf(dim, c)) || '#6B7682'} />}
            </g>
          )
        })}
        {extra.map((e) => <text key={e.cx} x={e.cx} y={20} className="strip-more" textAnchor="middle">+{e.n}</text>)}
      </svg>
      {hover ? (
        <div className="strip-tip" style={{ left: Math.min(width - 190, Math.max(0, hover.cx - 90)), top: Math.max(0, hover.cy - 64) }} role="tooltip">
          <b>{hover.c.collision_type ? hover.c.collision_type.toLowerCase() : 'crash'}</b><br />
          {hover.c.date}{hover.c.hour != null ? ` · ${String(hover.c.hour).padStart(2, '0')}:00` : ''} · {SEV[hover.c.severity] || hover.c.severity}
          {isVru(hover.c) ? <><br />{vruWho(hover.c)} involved</> : null}
        </div>
      ) : null}
      <div className="legend">{crashes.some(isVru) ? <span><i className="vru-key" />{RING_LEGEND}</span> : null}
        {cats.map((c) => <span key={c.key}><i style={c.hollow ? { background: 'transparent', boxShadow: `inset 0 0 0 1.5px ${c.color}` } : { background: c.color }} />{c.label}</span>)}</div>
    </div>
  )
}
