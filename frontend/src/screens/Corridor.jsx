import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import CorridorMap from '../components/CorridorMap'
import LocationPanel from '../components/LocationPanel'
import PlaceSearch from '../components/PlaceSearch'
import { api, errorText } from '../lib/api'
import { useStudy } from '../study'
import '../styles/corridor.css'

// Step 2: draw the corridor (on by default), then review the detected locations on the same screen.
export default function Corridor() {
  const { studyId } = useParams()
  const navigate = useNavigate()
  const { study, reload } = useStudy()
  const [net, setNet] = useState(null)
  const [draft, setDraft] = useState([])          // points while drawing or after moving A/B
  const [finished, setFinished] = useState(false) // draft line complete, ready to detect
  const [adding, setAdding] = useState(false)
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [fit, setFit] = useState({ key: null, points: null })

  useEffect(() => {
    let alive = true
    api(`/studies/${studyId}/network`)
      .then(async (n) => {
        if (!alive) return
        setNet(n)
        if (n.line) { setFit({ key: `load-${studyId}`, points: n.line }); return }
        // A context object imported from another tile (e.g. DemandIQ) can carry the corridor line: start from it.
        const pre = await api(`/studies/${studyId}/context/prefill`).catch(() => null)
        const line = pre?.prefill?.line
        if (alive && line?.length >= 2) {
          setDraft(line)
          setFinished(true)
          setFit({ key: `prefill-${studyId}`, points: line })
        }
      })
      .catch((e) => alive && setErr(errorText(e)))
    return () => { alive = false }
  }, [studyId])

  const saved = Boolean(net?.line)
  const dirty = saved && draft.length > 0           // A or B moved since detection
  const drawing = !saved && !finished
  const mode = drawing ? 'draw' : adding ? 'add' : 'review'
  const line = dirty || !saved ? draft : net.line

  const run = useCallback(async (label, fn) => {
    setBusy(label)
    setErr('')
    try { return await fn() } catch (e) { setErr(errorText(e)); return null } finally { setBusy('') }
  }, [])

  const detect = () => run('Finding intersections…', async () => {
    const n = await api(`/studies/${studyId}/corridor`, { method: 'PUT', body: { line } })
    setNet(n)
    setDraft([])
    setFinished(false)
    setFit({ key: `detect-${Date.now()}`, points: n.line })
  })

  const clear = () => run('', async () => {
    if (saved) setNet(await api(`/studies/${studyId}/corridor`, { method: 'DELETE' }))
    setDraft([])
    setFinished(false)
    setAdding(false)
  })

  const edit = (fn) => run('', async () => { setNet(await fn()) })

  const onMoveEnd = (idx, p) => {
    const base = dirty ? draft : (saved ? net.line : draft)
    const next = base.map((q, k) => (k === idx ? p : q))
    setDraft(next)
  }

  const onAddIntersection = (p) => run('', async () => {
    const before = new Set(net.intersections.map((i) => i.id))
    const n = await api(`/studies/${studyId}/intersections`, { method: 'POST', body: { lat: p[0], lon: p[1], name: '' } })
    setNet(n)
    setAdding(false)
    const added = n.intersections.find((i) => !before.has(i.id))
    if (added) setSelectedId(added.id)
  })

  const setSetting = (changes) => run('', async () => {
    await api(`/studies/${studyId}`, { method: 'PATCH', body: changes })
    await reload()
    setNet(await api(`/studies/${studyId}/network`))
  })

  const hint = useMemo(() => {
    if (drawing) return draft.length === 0
      ? 'Click on the street where the study starts (A), then along the street to the end.'
      : 'Keep clicking along the street. Double-click the last point to finish.'
    if (adding) return 'Click the map where the intersection is.'
    if (dirty) return 'Study limits moved. Find intersections again to update the list.'
    return null
  }, [drawing, draft.length, adding, dirty])

  return (
    <section className="corridor" aria-label="Corridor">
      <div className="mapwrap">
        <CorridorMap
          mode={mode}
          line={line}
          intersections={dirty ? [] : net?.intersections || []}
          radiusFt={study?.radius_ft ?? net?.radius_ft ?? 250}
          bufferRing={dirty ? null : net?.buffer_ring}
          selectedId={selectedId}
          onAddPoint={(p) => setDraft((d) => [...d, p])}
          onFinish={() => { if (draft.length >= 2) setFinished(true) }}
          onAddIntersection={onAddIntersection}
          onMoveEnd={onMoveEnd}
          onSelect={setSelectedId}
          fitKey={fit.key}
          fitPoints={fit.points}
        />
      </div>

      <div className="float toolbar" role="toolbar" aria-label="Map tools">
        <PlaceSearch onPick={(p) => setFit({ key: `search-${Date.now()}`, points: [p] })} />
        {drawing && draft.length > 0 ? (
          <button type="button" className="tool" onClick={() => setDraft((d) => d.slice(0, -1))}>Undo point</button>
        ) : null}
        {(saved || draft.length > 0) ? <button type="button" className="tool" onClick={clear}>Clear line</button> : null}
      </div>
      {hint ? <div className="float hint" role="status">{hint}</div> : null}

      <LocationPanel
        key={study ? `${study.id}:${study.radius_ft}:${study.buffer_ft}:${saved}` : 'loading'}
        net={net}
        study={study}
        drawing={drawing}
        draftPoints={draft.length}
        canDetect={(!saved && draft.length >= 2) || dirty}
        busy={busy}
        err={err}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onFinishDrawing={() => setFinished(true)}
        onDetect={detect}
        onStartAdd={() => setAdding((a) => !a)}
        adding={adding}
        onRename={(id, name) => edit(() => api(`/studies/${studyId}/intersections/${id}`, { method: 'PATCH', body: { name } }))}
        onToggleStudy={(id, isStudy) => edit(() => api(`/studies/${studyId}/intersections/${id}`, { method: 'PATCH', body: { is_study: isStudy } }))}
        onRemove={(id) => edit(() => api(`/studies/${studyId}/intersections/${id}`, { method: 'DELETE' }))}
        onIntersectionAadt={(id, body) => edit(() => api(`/studies/${studyId}/intersections/${id}`, { method: 'PATCH', body }))}
        onSegmentAadt={(id, aadt) => edit(() => api(`/studies/${studyId}/segments/${encodeURIComponent(id)}`, { method: 'PATCH', body: { aadt } }))}
        onSetting={setSetting}
        onBack={() => navigate(`/s/${studyId}/setup`)}
        onNext={() => navigate(`/s/${studyId}/profile`)}
      />
    </section>
  )
}
