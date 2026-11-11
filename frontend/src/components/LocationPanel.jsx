import { useEffect, useRef, useState } from 'react'

const CONTROL = { signal: 'Signal', stop: 'Stop', roundabout: 'Roundabout', unknown: null }
const fmtMi = (mi) => `${mi.toFixed(2)} mi`

function NameCell({ it, editing, setEditing, onRename }) {
  const [val, setVal] = useState(it.name)
  const ref = useRef(null)
  useEffect(() => { if (editing) ref.current?.select() }, [editing])
  if (!editing) {
    return (
      <button type="button" className="n" title="Rename" onClick={() => { setVal(it.name); setEditing(true) }}>
        {it.name}
      </button>
    )
  }
  const save = () => { setEditing(false); if (val.trim() && val.trim() !== it.name) onRename(it.id, val.trim()) }
  return (
    <input ref={ref} className="input rename" aria-label={`Rename ${it.name}`} value={val}
      onChange={(e) => setVal(e.target.value)} onBlur={save}
      onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false) }} />
  )
}

function AadtInput({ label, short, value, onCommit }) {
  const [v, setV] = useState(value ?? '')
  const commit = () => {
    const num = v === '' ? null : Number(v)
    if (num !== (value ?? null) && (num === null || Number.isFinite(num))) onCommit(num)
  }
  return (
    <label className="aadt">
      <span aria-hidden="true">{short}</span>
      <input className="input" inputMode="numeric" type="number" min="0" step="100" value={v}
        aria-label={label} onChange={(e) => setV(e.target.value)} onBlur={commit}
        onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur() }} />
    </label>
  )
}

function SegmentRow({ seg, rates, onSegmentAadt, peak }) {
  return (
    <div className="loc seg">
      <span aria-hidden="true" />
      <span className="mono">{fmtMi(seg.length_mi)}</span>
      {rates ? <AadtInput key={`${seg.id}-${seg.aadt}`} label={`Segment ${peak ? 'peak-hour volume' : 'AADT'}, ${seg.name}`} short={peak ? 'Peak hr' : 'AADT'} value={seg.aadt}
        onCommit={(a) => onSegmentAadt(seg.id, a)} /> : <span />}
    </div>
  )
}

export default function LocationPanel({
  net, study, drawing, draftPoints, canDetect, busy, err, selectedId, onSelect,
  onDetect, onStartAdd, adding, onRename, onToggleStudy, onRemove, onIntersectionAadt, onSegmentAadt,
  onSetting, onBack, onNext,
}) {
  const [editingId, setEditingId] = useState(null)
  const anyAadt = Boolean(net?.segments?.some((s) => s.aadt != null) || net?.intersections?.some((i) => i.major_aadt != null))
  const [rates, setRates] = useState(anyAadt)
  const peak = study?.volume_basis === 'peak_hour'
  const vol = peak ? 'peak-hour volume' : 'AADT'
  const volShort = peak ? 'peak hr' : 'AADT'
  const [radius, setRadius] = useState(study?.radius_ft ?? 250)
  const [buffer, setBuffer] = useState(study?.buffer_ft ?? 100)
  const listRef = useRef(null)

  useEffect(() => {
    if (!selectedId) return
    listRef.current?.querySelector(`[data-id="${CSS.escape(selectedId)}"]`)?.scrollIntoView({ block: 'nearest' })
  }, [selectedId])

  const saved = Boolean(net?.line)
  const ints = net?.intersections || []
  const segs = net?.segments || []
  const segFrom = Object.fromEntries(segs.map((s) => [s.from_id, s]))
  const nStudy = ints.filter((i) => i.is_study).length

  // Interleave: each segment row sits just before the study intersection where it ends.
  const rows = []
  let pending = segFrom.A || null
  if (pending) rows.push({ kind: 'end', label: 'A', name: 'Study start (A)' })
  let n = 0
  for (const it of ints) {
    if (it.is_study && pending) { rows.push({ kind: 'seg', seg: pending }); pending = null }
    rows.push({ kind: 'int', it, n: it.is_study ? ++n : null })
    if (it.is_study) pending = segFrom[it.id] || null
  }
  if (pending) { rows.push({ kind: 'seg', seg: pending }); rows.push({ kind: 'end', label: 'B', name: 'Study end (B)' }) }

  let primary
  if (canDetect) primary = <button type="button" className="sf-btn sf-btn--go" onClick={onDetect} disabled={Boolean(busy)}>{busy || (err ? 'Try again' : 'Find intersections →')}</button>
  else if (saved) primary = <button type="button" className="sf-btn sf-btn--go" onClick={onNext} disabled={Boolean(busy)}>Build the profile →</button>
  else primary = <button type="button" className="sf-btn sf-btn--go" disabled>Find intersections →</button>

  return (
    <aside className="float side" aria-label="Corridor locations">
      <div className="hd">
        <h2 className="h2">{net?.corridor_name || (saved ? 'Corridor' : 'Draw the corridor')}</h2>
        {saved ? (
          <div className="muted mono sub">{fmtMi(net.length_mi)} · {nStudy} study intersection{nStudy === 1 ? '' : 's'}</div>
        ) : (
          <div className="muted sub">{drawing ? `${draftPoints} point${draftPoints === 1 ? '' : 's'} drawn` : 'Line finished'}</div>
        )}
      </div>

      <div className="bd" ref={listRef}>
        {saved && (
          <>
            {ints.length === 0 ? (
              <p className="muted">No intersections found along this line. Check that it follows a street, or add them yourself.</p>
            ) : (
              <div className="loclist" role="list">
                {rows.map((r, k) => {
                  if (r.kind === 'end') return (
                    <div key={`e-${r.label}`} className="loc endrow" role="listitem">
                      <span className="pin end">{r.label}</span><span className="muted">{r.name}</span><span />
                    </div>
                  )
                  if (r.kind === 'seg') return <SegmentRow key={`s-${r.seg.id}-${k}`} seg={r.seg} rates={rates} peak={peak} onSegmentAadt={onSegmentAadt} />
                  const it = r.it
                  return (
                    <div key={it.id} data-id={it.id} role="listitem"
                      className={`loc${it.is_study ? '' : ' off'}${it.id === selectedId ? ' sel' : ''}`}
                      onMouseEnter={() => onSelect(it.id)}>
                      <span className="pin">{r.n ?? '·'}</span>
                      <div className="body">
                        <NameCell it={it} editing={editingId === it.id}
                          setEditing={(on) => setEditingId(on ? it.id : null)} onRename={onRename} />
                        <div className="m">
                          {CONTROL[it.control] ? <span className="tier">{CONTROL[it.control]}</span> : null}
                          {it.legs === 3 ? <span className="tier" title="Cross street on one side only">T</span> : null}
                          {it.provenance === 'manual' ? <span className="tier">Added by you</span> : null}
                        </div>
                        {rates && it.is_study ? (
                          <div className="aadts">
                            <AadtInput key={`ma-${it.id}-${it.major_aadt}`} label={`Major road two-way ${vol}, ${it.name}`} short={`Major ${volShort}`} value={it.major_aadt}
                              onCommit={(a) => onIntersectionAadt(it.id, { major_aadt: a })} />
                            <AadtInput key={`mi-${it.id}-${it.minor_aadt}`} label={`Minor road two-way ${vol}, ${it.name}`} short={`Minor ${volShort}`} value={it.minor_aadt}
                              onCommit={(a) => onIntersectionAadt(it.id, { minor_aadt: a })} />
                            <label className="aadt">
                              <span>Legs</span>
                              <select className="input" aria-label={`Legs, ${it.name}`} value={it.legs ?? ''}
                                title="A T (3 legs) counts half the minor road's AADT as entering"
                                onChange={(e) => onIntersectionAadt(it.id, { legs: e.target.value ? Number(e.target.value) : null })}>
                                <option value="">?</option>
                                {[3, 4, 5, 6].map((n) => <option key={n} value={n}>{n}</option>)}
                              </select>
                            </label>
                          </div>
                        ) : null}
                      </div>
                      <div className="acts">
                        <input type="checkbox" checked={it.is_study} aria-label={`Study intersection: ${it.name}`}
                          title="Study intersection" onChange={(e) => onToggleStudy(it.id, e.target.checked)} />
                        <button type="button" className="x" aria-label={`Remove ${it.name}`} title="Remove"
                          onClick={() => onRemove(it.id)}>×</button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
            <button type="button" className="linkbtn" aria-pressed={adding} onClick={onStartAdd}>
              {adding ? 'Cancel adding' : '+ Add intersection'}
            </button>

            <details className="adv">
              <summary>More options</summary>
              <div className="opts">
                <div className="field">
                  <label htmlFor="radius">Intersection influence radius <span className="mono">{radius} ft</span></label>
                  <input id="radius" type="range" className="slider" min="100" max="500" step="25" value={radius}
                    onChange={(e) => setRadius(Number(e.target.value))}
                    onPointerUp={() => onSetting({ radius_ft: radius })}
                    onKeyUp={() => onSetting({ radius_ft: radius })} />
                </div>
                <div className="field">
                  <label htmlFor="buffer">Corridor buffer (ft each side)</label>
                  <input id="buffer" className="input" type="number" min="10" max="500" step="5" value={buffer}
                    onChange={(e) => setBuffer(e.target.value === '' ? '' : Number(e.target.value))}
                    onBlur={() => { if (buffer !== '' && buffer !== study?.buffer_ft) onSetting({ buffer_ft: buffer }) }} />
                </div>
                <label className="check">
                  <input type="checkbox" checked={rates} onChange={(e) => setRates(e.target.checked)} />
                  <span>Enter AADT to compute rates</span>
                </label>
                {rates ? (
                  <div className="field vbasis">
                    <label htmlFor="vbasis">Volumes entered as</label>
                    <div className="row">
                      <select id="vbasis" className="input" value={study?.volume_basis || 'aadt'}
                        onChange={(e) => onSetting({ volume_basis: e.target.value })}>
                        <option value="aadt">Daily (AADT)</option>
                        <option value="peak_hour">Peak hour (converted with K)</option>
                      </select>
                      {peak ? (
                        <label className="kf">K
                          <input className="input" type="number" min="4" max="25" step="0.5" aria-label="K factor, percent of daily traffic"
                            defaultValue={Math.round((study?.k_factor ?? 0.1) * 1000) / 10}
                            onBlur={(e) => { const v = Number(e.target.value) / 100; if (v && v !== study?.k_factor) onSetting({ k_factor: v }) }} />%
                        </label>
                      ) : null}
                    </div>
                  </div>
                ) : null}
                <label className="check">
                  <input type="checkbox" checked={Boolean(study?.include_freeway)}
                    onChange={(e) => onSetting({ include_freeway: e.target.checked })} />
                  <span>Include freeway and ramp crashes (ramp-terminal studies)</span>
                </label>
              </div>
            </details>
          </>
        )}
        {!saved && !drawing ? <p className="muted">Ready. Find the intersections along the line.</p> : null}
        {err ? <div className="err" role="alert">{err}</div> : null}
      </div>

      <div className="ft cta-bar">
        <button type="button" className="sf-btn quiet" onClick={onBack}>Back</button>
        {primary}
      </div>
    </aside>
  )
}
