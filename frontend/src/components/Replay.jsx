import { useEffect, useRef, useState } from 'react'

// Pattern replay: a schematic animation of the finding's conflict, then the real records appear one by one.
// Schematic only: vehicle paths illustrate the crash type, not any single crash.
const LABELS = {
  broadside: 'Right-angle conflict', night: 'Nighttime conflict', sideswipe: 'Same-direction lane conflict',
  rear_end: 'Rear-end conflict', head_on: 'Opposing-direction conflict', ped: 'Vehicle–pedestrian conflict',
  generic: 'Single-vehicle conflict',
}
const PHASES = ['1 · Approach', '2 · Conflict', '3 · The records']
const LOOP = 10

const css = (n, fb) => (typeof document !== 'undefined'
  && getComputedStyle(document.documentElement).getPropertyValue(n).trim()) || fb
const ease = (x) => (x < 0 ? 0 : x > 1 ? 1 : 1 - (1 - x) ** 3)
const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function phaseAt(t) {
  return t < 3.2 ? 0 : t < 5 ? 1 : 2
}

function draw(ctx, W, H, t, anim, segment, records) {
  const c = {
    road: css('--road', '#2A3036'), verge: css('--road-verge', '#14181C'), paint: css('--paint', '#E6EAEE'),
    y: css('--paint-yellow', '#FFC83D'), car: css('--car', '#8E9AA6'), stop: css('--lamp-stop', '#FF5A4E'),
    amber: css('--lamp-amber', '#FFB020'), go: css('--lamp-go', '#1EE39A'), fg: '#E6EAEE',
  }
  const night = anim === 'night'
  const cx = W * 0.5, cy = H * 0.5, HALF = Math.round(H * 0.13), sc = HALF / 34
  const CROSS = segment ? Math.round(HALF * 0.45) : HALF               // a driveway on a segment, a street at a node
  ctx.fillStyle = c.verge; ctx.fillRect(0, 0, W, H)
  ctx.fillStyle = c.road
  ctx.fillRect(cx - HALF, 0, HALF * 2, H)                                 // corridor runs north–south
  if (segment) ctx.fillRect(0, cy - CROSS, cx - HALF, CROSS * 2)
  else ctx.fillRect(0, cy - CROSS, W, CROSS * 2)
  ctx.strokeStyle = c.y; ctx.globalAlpha = 0.8; ctx.lineWidth = 1
  const lines = [[cx - 1.5, 0, cx - 1.5, cy - CROSS - 12], [cx + 1.5, 0, cx + 1.5, cy - CROSS - 12],
    [cx - 1.5, cy + CROSS + 12, cx - 1.5, H], [cx + 1.5, cy + CROSS + 12, cx + 1.5, H]]
  if (!segment) {
    lines.push([0, cy - 1.5, cx - HALF - 12, cy - 1.5], [0, cy + 1.5, cx - HALF - 12, cy + 1.5],
      [cx + HALF + 12, cy - 1.5, W, cy - 1.5], [cx + HALF + 12, cy + 1.5, W, cy + 1.5])
  }
  for (const l of lines) { ctx.beginPath(); ctx.moveTo(l[0], l[1]); ctx.lineTo(l[2], l[3]); ctx.stroke() }
  ctx.globalAlpha = 0.35; ctx.fillStyle = c.paint
  ctx.setLineDash([8, 10]); ctx.strokeStyle = c.paint
  ctx.beginPath(); ctx.moveTo(cx + HALF / 2, 0); ctx.lineTo(cx + HALF / 2, H); ctx.moveTo(cx - HALF / 2, 0); ctx.lineTo(cx - HALF / 2, H); ctx.stroke()
  ctx.setLineDash([])
  if (!segment || anim === 'ped') {
    for (let k = -HALF + 3; k < HALF; k += 8) { ctx.fillRect(cx + k, cy - CROSS - 14, 3.5, 11); ctx.fillRect(cx + k, cy + CROSS + 3, 3.5, 11) }
  }
  ctx.globalAlpha = 1
  if (night) {
    for (const p of [[cx - HALF - 20, cy - HALF - 20], [cx + HALF + 20, cy + HALF + 20]]) {
      const g = ctx.createRadialGradient(p[0], p[1], 2, p[0], p[1], 70 * sc)
      g.addColorStop(0, 'rgba(255,214,140,.22)'); g.addColorStop(1, 'rgba(255,214,140,0)')
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p[0], p[1], 70 * sc, 0, Math.PI * 2); ctx.fill()
    }
    ctx.fillStyle = 'rgba(0,0,0,.35)'; ctx.fillRect(0, 0, W, H)
  }
  const phase = phaseAt(t)
  const car = (x, y, ang, col, label, below) => {
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang); ctx.scale(sc, sc)
    if (phase < 2) { ctx.shadowColor = col; ctx.shadowBlur = 14 }
    ctx.fillStyle = col; ctx.beginPath()
    if (ctx.roundRect) ctx.roundRect(-8, -4.5, 16, 9, 2); else ctx.rect(-8, -4.5, 16, 9)
    ctx.fill(); ctx.shadowBlur = 0
    ctx.fillStyle = '#FFF4CF'; ctx.fillRect(6.5, -3.5, 1.6, 1.6); ctx.fillRect(6.5, 2, 1.6, 1.6)
    if (night) {
      const g = ctx.createLinearGradient(8, 0, 60, 0)
      g.addColorStop(0, 'rgba(255,244,207,.35)'); g.addColorStop(1, 'rgba(255,244,207,0)')
      ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(8, -3); ctx.lineTo(60, -14); ctx.lineTo(60, 14); ctx.lineTo(8, 3); ctx.fill()
    }
    ctx.restore()
    if (label && phase < 2) {
      ctx.fillStyle = col; ctx.font = '600 10px "Overpass Mono", monospace'
      ctx.fillText(label, x + 12 * sc, below ? y + 20 * sc : y - 10 * sc)
    }
  }
  const A = c.car, B = c.amber, k1 = ease(Math.min(t, 4.2) / 4.2), after = Math.max(0, t - 4.2)
  const NB = -Math.PI / 2
  let impact
  if (anim === 'broadside' || anim === 'night') {
    let ay = H + 20 - (H + 20 - (cy + 8 * sc)) * k1
    let bx = -20 + (cx - 14 * sc + 20) * k1
    ay -= after * 6; bx += after * 5
    car(cx + 10 * sc, Math.max(ay, cy + 4 * sc), NB, A, 'A · through')
    car(Math.min(bx, cx - 4 * sc), cy + 6 * sc, 0, B, segment ? 'B · from driveway' : 'B · crossing', true)
    impact = [cx + 2 * sc, cy + 8 * sc]
  } else if (anim === 'rear_end') {
    const stopY = cy + CROSS + 30 * sc
    const by = H + 20 - (H + 20 - (stopY + 18 * sc)) * k1
    car(cx + 17 * sc, stopY, NB, A, 'A · stopped')
    car(cx + 17 * sc, by, NB, B, 'B · following', true)
    impact = [cx + 17 * sc, stopY + 9 * sc]
  } else if (anim === 'head_on') {
    const drift = ease((t - 1.5) / 2.5) * 16
    car(cx + 17 * sc, H + 20 - (H / 2 - 8 * sc + 20) * k1, NB, A, 'A · northbound')
    car(cx - (17 - drift) * sc, -20 + (H / 2 - 10 * sc + 20) * k1, Math.PI / 2 + 0.12 * ease((t - 1.5) / 2), B, 'B · crosses centerline')
    impact = [cx + 2 * sc, cy]
  } else if (anim === 'ped') {
    const py = cy - CROSS - 8
    const px = cx - HALF - 20 + (HALF + 12) * ease(t / 4.2)
    car(cx + 10 * sc, H + 20 - (H + 20 - (py + 14 * sc)) * k1, NB, A, 'A · turning or through')
    ctx.fillStyle = B; ctx.beginPath(); ctx.arc(px, py, 4.5 * sc, 0, Math.PI * 2); ctx.fill()
    if (phase < 2) { ctx.font = '600 10px "Overpass Mono", monospace'; ctx.fillText('pedestrian', px - 30 * sc, py - 10 * sc) }
    impact = [cx + 6 * sc, py + 4 * sc]
  } else if (anim === 'sideswipe') {
    const y1 = H + 20 - H * 0.62 * k1, drift = ease((t - 2) / 2.2) * 12
    car(cx + 9 * sc, y1, NB, A, 'A')
    car(cx + (25 - drift) * sc, y1 + 6 * sc, NB - 0.08 * ease((t - 2) / 2), B, 'B · lane change')
    impact = [cx + 16 * sc, y1 + 2 * sc]
  } else {
    const drift = ease((t - 1.5) / 2.7) * 18
    const ay = H + 20 - (H * 0.55) * k1
    ctx.fillStyle = c.paint; ctx.fillRect(cx + HALF + 4 * sc, cy - 4 * sc, 7 * sc, 7 * sc)
    car(cx + (17 + drift) * sc, ay, NB + 0.25 * ease((t - 1.5) / 2.7), A, 'A · leaves the lane')
    impact = [cx + HALF + 6 * sc, cy]
  }
  if (t > 4 && t < 5.2) {
    ctx.strokeStyle = c.stop; ctx.globalAlpha = 1 - (t - 4) / 1.2; ctx.lineWidth = 3
    ctx.beginPath(); ctx.arc(impact[0], impact[1], (t - 4) * 60, 0, Math.PI * 2); ctx.stroke(); ctx.globalAlpha = 1
  }
  if (t > 5 && records.length) {
    const shown = Math.min(records.length, Math.floor((t - 5) * 6))
    for (let i = 0; i < shown; i++) {
      const a = (i * 2.399) % (Math.PI * 2), d = 16 + (i * 13) % 44
      const s = records[i].severity
      const col = s === 'K' || s === 'A' ? c.stop : s === 'O' ? c.car : c.amber
      ctx.fillStyle = col; ctx.shadowColor = col; ctx.shadowBlur = 8
      ctx.beginPath(); ctx.arc(impact[0] + Math.cos(a) * d * sc, impact[1] + Math.sin(a) * d * 0.8 * sc, 3.6, 0, Math.PI * 2); ctx.fill()
      ctx.shadowBlur = 0
    }
    const label = `${shown} / ${records.length} records`
    ctx.font = '700 13px "Overpass Mono", monospace'
    const tw = ctx.measureText(label).width
    const lx = Math.min(impact[0] + 52, W - tw - 30)
    ctx.fillStyle = 'rgba(7,9,11,.8)'; ctx.fillRect(lx, impact[1] - 34, tw + 18, 26)
    ctx.fillStyle = c.fg; ctx.fillText(label, lx + 9, impact[1] - 16)
  }
  return phase
}

export default function Replay({ anim = 'generic', segment = false, records = [] }) {
  const ref = useRef(null)
  const st = useRef({ t: 0 })   // plays only once the user asks for it (#268: no Pause / Replay)
  const [phase, setPhase] = useState(0)
  const kind = LABELS[anim] ? anim : 'generic'

  useEffect(() => {
    const cv = ref.current
    const ctx = cv?.getContext?.('2d')
    if (!ctx) return undefined
    const still = reducedMotion()
    st.current.t = still ? 7.5 : 0
    let raf = 0, last = performance.now(), shownPhase = -1
    const frame = (now) => {
      const dt = Math.min(0.05, (now - last) / 1000); last = now
      if (!still) st.current.t = (st.current.t + dt) % LOOP
      const r = cv.getBoundingClientRect()
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      if (cv.width !== Math.round(r.width * dpr)) { cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr) }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      const p = draw(ctx, r.width, r.height, st.current.t, kind, segment, records)
      if (p !== shownPhase) { shownPhase = p; setPhase(p) }
      raf = requestAnimationFrame(frame)
    }
    raf = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(raf)
  }, [kind, segment, records])

  return (
    <div className="replay sf-road">
      <canvas ref={ref} aria-label={`Pattern replay: ${LABELS[kind]}, schematic`} role="img" />
      <div className="sf-chip">
        <span className="sf-sig" data-s="r"><i /><i /><i /></span>
        <span>Pattern replay<small>{LABELS[kind]} · schematic</small></span>
      </div>
      <div className="phases">
        {PHASES.map((p, i) => <span key={p} className={i === phase ? 'on' : ''}>{p}</span>)}
      </div>
    </div>
  )
}
