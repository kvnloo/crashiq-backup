// Schematic collision diagram: one glyph per record, shaped by collision type, colored by severity.
// Glyphs are arranged in a grid around the conflict area; positions are schematic, not surveyed.
const SEV = { K: 'var(--sev-k)', A: 'var(--sev-a)', B: 'var(--sev-i)', C: 'var(--sev-i)', U: 'var(--sev-i)', O: 'var(--sev-p)' }

function Glyph({ type, x, y, color }) {
  const t = (type || '').toUpperCase()
  const dot = <circle r="2.5" fill="var(--stop)" stroke="none" />
  const g = (d, extra) => (
    <g transform={`translate(${x},${y})`} stroke={color} strokeWidth="2" fill="none" strokeLinecap="round">
      <path d={d} />{extra}
    </g>
  )
  if (t === 'BROADSIDE') return g('M-8 0h8M0 8v-8', dot)
  if (t === 'REAR END') return g('M0 10v-5M0 2v-10', <circle cy="3.5" r="2.5" fill="var(--stop)" stroke="none" />)
  if (t === 'SIDE SWIPE') return g('M-3 8v-14M3 8v-14', dot)
  if (t === 'HEAD-ON') return g('M0 10v-8M0 -10v8', dot)
  if (t.includes('PEDESTRIAN')) return g('M0 9v-9M-6 -4h12', <circle cy="-8" r="2" fill={color} stroke="none" />)
  if (t === 'HIT OBJECT') return g('M0 9v-7', <rect x="-3.5" y="-8" width="7" height="7" fill={color} stroke="none" />)
  return <g transform={`translate(${x},${y})`}><circle r="3.5" fill={color} /></g>
}

export default function CollisionDiagram({ records = [], corridor = 'Corridor', cross = '', segment = false }) {
  const cols = 8
  const W = 320, H = 320, c = 160, half = 34, ch = segment ? 14 : half
  const placed = records.map((r, i) => ({
    r, x: c - ((Math.min(cols, records.length) - 1) * 18) / 2 + (i % cols) * 18,
    y: c - (Math.ceil(records.length / cols) - 1) * 9 + Math.floor(i / cols) * 18,
  }))
  return (
    <div className="diagram">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Collision diagram, ${records.length} records, schematic`}>
        <rect x={c - half} y="0" width={half * 2} height={H} fill="var(--surface-2)" />
        <rect x="0" y={c - ch} width={segment ? c - half : W} height={ch * 2} fill="var(--surface-2)" />
        <path d={`M${c} 0v${c - ch}M${c} ${c + ch}v${H}`} stroke="var(--line)" strokeDasharray="6 6" />
        {!segment && <path d={`M0 ${c}h${c - half}M${c + half} ${c}h${W}`} stroke="var(--line)" strokeDasharray="6 6" />}
        <text x={c + half + 6} y="14" fill="var(--muted)" fontFamily="var(--font-mono)" fontSize="10">{corridor.toUpperCase()}</text>
        <text x="6" y={c - ch - 6} fill="var(--muted)" fontFamily="var(--font-mono)" fontSize="10">{(segment ? 'driveways / midblock' : cross).toUpperCase()}</text>
        {placed.map(({ r, x, y }) => <Glyph key={r.crash_id} type={r.collision_type} x={x} y={y} color={SEV[r.severity] || 'var(--sev-p)'} />)}
      </svg>
      <div className="legend">
        <span><i style={{ background: 'var(--sev-k)' }} />fatal</span>
        <span><i style={{ background: 'var(--sev-a)' }} />serious injury</span>
        <span><i style={{ background: 'var(--sev-i)' }} />other injury</span>
        <span><i style={{ background: 'var(--sev-p)' }} />property damage</span>
        <span className="muted">schematic · one glyph per record</span>
      </div>
    </div>
  )
}
