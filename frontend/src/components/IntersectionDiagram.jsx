// G. Collision diagram (#106, user decision N10): the backend places every symbol (backend/crashiq/diagram.py) and
// sends drawing steps; this only draws them, so the app and the PDF show the same diagram. Numbers on the diagram
// key to the crash list (T21). Colours: text ink for symbols, the KABCO ramp only for the severity ring.
const COLOR = { ink: 'var(--diag-ink)', arm: '#969696', muted: 'var(--diag-muted)', paper: 'var(--diag-paper)',
  sev_k: 'var(--sev-k)', sev_a: 'var(--sev-a)', sev_b: 'var(--sev-b)', sev_c: 'var(--sev-c)', sev_u: 'var(--sev-u)', sev_o: 'var(--sev-o)' }
const c = (k) => COLOR[k] || k

function Step({ s }) {
  switch (s.op) {
    case 'rect_cell':
      return <rect width={s.w} height={s.h} fill={c('paper')} stroke={c('ink')} />
    case 'line':
      return <path d={`M${s.pts.map((p) => p.join(',')).join(' L')}`} fill="none" stroke={c(s.color)} strokeWidth={s.w}
        strokeDasharray={s.dash ? `${1.5 * s.w} ${3 * s.w}` : undefined} strokeLinecap="round" strokeLinejoin="round" />
    case 'head':
      return <path d="M0,-4 L3.4,3 L-3.4,3 Z" transform={`translate(${s.x},${s.y}) rotate(${s.ang}) scale(${s.size || 1})`}
        fill={s.filled ? c(s.color) : c('paper')} stroke={c(s.color)} strokeWidth={1.3} strokeLinejoin="round" />
    case 'circle':
      return <circle cx={s.x} cy={s.y} r={s.r} fill={c(s.fill)} stroke={c(s.stroke)} strokeWidth={s.w} />
    case 'poly':
      return <polygon points={s.pts.map((p) => p.join(',')).join(' ')} fill={c(s.fill)} stroke={c(s.stroke)} strokeWidth={s.w} />
    case 'text':
      return <text x={s.x} y={s.y} fontSize={s.size} fontWeight={s.bold ? 700 : 400} fill={c(s.color)}
        textAnchor={s.anchor === 'start' ? 'start' : s.anchor === 'end' ? 'end' : 'middle'}
        transform={s.rot ? `rotate(${s.rot} ${s.x} ${s.y})` : undefined}>{s.t}</text>
    case 'north':
      return <g transform={`translate(${s.x},${s.y})`}><path d="M0,-18 L7,4 L0,-2 L-7,4 Z" fill={c('ink')} />
        <text x="0" y="18" fontSize="11" fontWeight="700" textAnchor="middle" fill={c('ink')}>N</text></g>
    default:
      return null
  }
}

function Steps({ steps }) {
  return steps.map((s, i) => <Step key={i} s={s} />)
}

export default function IntersectionDiagram({ diagram, label }) {
  return (
    <svg className="cdiag" viewBox={`0 0 ${diagram.width} ${diagram.height}`} role="img" data-testid="collision-diagram"
      aria-label={`Collision diagram, ${label}: ${diagram.crashes.length} crashes`}>
      <Steps steps={diagram.steps} />
    </svg>
  )
}
IntersectionDiagram.Steps = Steps
