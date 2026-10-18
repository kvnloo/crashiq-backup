import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import SignalFlowHero from '../lib/signal-flow/SignalFlowHero'
import { api, errorText } from '../lib/api'
import { useStudy } from '../study'
import '../styles/setup.css'

const CUSTOM = 'custom'

// Step 1. Headline above the live traffic sim (never on top of it), then one row of inputs and one green action.
export default function Setup() {
  const { studyId } = useParams()
  const { study } = useStudy()
  const [meta, setMeta] = useState(null)
  const [metaErr, setMetaErr] = useState('')

  useEffect(() => {
    api('/studies/meta').then(setMeta).catch((e) => setMetaErr(errorText(e)))
  }, [])

  const waitingForStudy = Boolean(studyId) && !study
  return (
    <section className="setup" aria-label="Setup">
      <div className="intro">
        <h1 className="h1">What&rsquo;s going wrong on this corridor?</h1>
        <p className="muted">Draw a corridor. CrashIQ pulls every reported crash and shows you the patterns, traced back to the records.</p>
      </div>
      <SignalFlowHero />
      {meta && !waitingForStudy
        ? <SetupForm key={study?.id || 'new'} meta={meta} study={study} />
        : <div className="muted">{metaErr || 'Loading…'}</div>}
    </section>
  )
}

function initialWindow(meta, study) {
  if (!study) return { win: String(meta.default_window.to_year - meta.default_window.from_year + 1), custom: { from: '', to: '' } }
  const match = meta.window_options.find((o) => o.from_year === study.from_year && o.to_year === study.to_year)
  return match
    ? { win: String(match.years), custom: { from: '', to: '' } }
    : { win: CUSTOM, custom: { from: String(study.from_year), to: String(study.to_year) } }
}

function SetupForm({ meta, study }) {
  const navigate = useNavigate()
  const { setStudy } = useStudy()
  const init = initialWindow(meta, study)
  const [name, setName] = useState(study?.name || '')
  const [mode, setMode] = useState(study?.mode || meta.default_mode)
  const [win, setWin] = useState(init.win)
  const [custom, setCustom] = useState(init.custom)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const years = useMemo(() => {
    if (!meta) return []
    const out = []
    for (let y = meta.last_year; y >= meta.first_year; y -= 1) out.push(y)
    return out
  }, [meta])

  const chosen = useMemo(() => {
    if (!meta) return null
    if (win === CUSTOM) {
      const fy = Number(custom.from)
      const ty = Number(custom.to)
      return fy && ty ? { from_year: fy, to_year: ty, covid: fy <= 2020 && 2020 <= ty } : null
    }
    const o = meta.window_options.find((x) => String(x.years) === win)
    return o ? { from_year: o.from_year, to_year: o.to_year, covid: o.covid } : null
  }, [meta, win, custom])

  async function submit(e) {
    e.preventDefault()
    if (!chosen) { setErr('Pick the crash history years.'); return }
    setBusy(true)
    setErr('')
    try {
      const body = { name: name.trim(), mode, from_year: chosen.from_year, to_year: chosen.to_year }
      const s = study
        ? await api(`/studies/${study.id}`, { method: 'PATCH', body })
        : await api('/studies', { method: 'POST', body })
      setStudy(s)
      navigate(`/s/${s.id}/corridor`)
    } catch (ex) {
      setErr(errorText(ex))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <form className="startbar" onSubmit={submit}>
        <div className="field">
          <label htmlFor="mode">Study</label>
          <select id="mode" className="input" value={mode} onChange={(e) => setMode(e.target.value)} disabled={!meta}>
            {(meta?.modes || []).map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="pname">Project</label>
          <input id="pname" className="input" value={name} onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Crenshaw Blvd safety" required maxLength={200} />
        </div>
        <div className="field">
          <label htmlFor="years">Crash history</label>
          <select id="years" className="input" value={win} onChange={(e) => setWin(e.target.value)} disabled={!meta}>
            {(meta?.window_options || []).map((o) => <option key={o.years} value={String(o.years)}>{o.label}</option>)}
            <option value={CUSTOM}>Custom range</option>
          </select>
        </div>
        <button type="submit" className="sf-btn sf-btn--go" disabled={!meta || busy || !name.trim()}>
          {busy ? 'Saving…' : 'Draw the corridor →'}
        </button>
        {win === CUSTOM && (
          <div className="custom" role="group" aria-label="Custom range">
            <div className="field">
              <label htmlFor="fromYear">From</label>
              <select id="fromYear" className="input" value={custom.from} onChange={(e) => setCustom((c) => ({ ...c, from: e.target.value }))}>
                <option value="">Year</option>
                {years.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="toYear">To</label>
              <select id="toYear" className="input" value={custom.to} onChange={(e) => setCustom((c) => ({ ...c, to: e.target.value }))}>
                <option value="">Year</option>
                {years.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
          </div>
        )}
      </form>
      {chosen?.covid ? <div className="note">Includes 2020 (COVID year). The report will flag it.</div> : null}
      {err ? <div className="err" role="alert">{err}</div> : null}
    </>
  )
}
