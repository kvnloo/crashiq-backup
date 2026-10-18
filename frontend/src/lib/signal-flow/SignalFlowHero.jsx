import { useEffect, useRef, useState } from 'react'
import './signal-flow.js'

const NAMES = { g: 'Green', y: 'Yellow', r: 'Red' }

// Live four-leg signalized intersection with a phase chip (JSX port of the repo's SignalFlowHero.tsx).
export default function SignalFlowHero({ mainLabel = 'Φ2/Φ6 Main St', sideLabel = 'Φ4/Φ8 Cross St', speed = 3 }) {
  const canvasRef = useRef(null)
  const [chip, setChip] = useState({ state: 'g', title: `${mainLabel} · Green`, sub: '' })

  useEffect(() => {
    const SF = window.SignalFlow
    if (!canvasRef.current || !SF || !canvasRef.current.getContext('2d')) return undefined
    let lastKey = ''
    const api = SF.intersection(canvasRef.current, {
      speed,
      onTick: (a) => {
        const m = a.main()
        const s = a.side()
        const mainHas = m.state !== 'r'
        const on = mainHas ? m : s
        const allRed = m.state === 'r' && s.state === 'r'
        const left = Math.ceil(on.left)
        const key = `${on.state}${mainHas}${left}${allRed}`
        if (key === lastKey) return
        lastKey = key
        setChip({
          state: on.state,
          title: allRed ? 'All red clearance' : `${mainHas ? mainLabel : sideLabel} · ${NAMES[on.state]}`,
          sub: `C = ${m.cycle} s · ${left} s left · shown at ${speed}×`,
        })
      },
    })
    return () => api.destroy()
  }, [mainLabel, sideLabel, speed])

  return (
    <div className="sf-road">
      <canvas ref={canvasRef} aria-hidden="true" />
      <div className="sf-chip" aria-hidden="true">
        <span className="sf-sig sf-sig--lg" data-s={chip.state}><i /><i /><i /></span>
        <div><span>{chip.title}</span><small>{chip.sub}</small></div>
      </div>
    </div>
  )
}
