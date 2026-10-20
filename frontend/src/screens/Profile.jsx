import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import ProfileMap from '../components/ProfileMap'
import ReviewList from '../components/ReviewList'
import { locationPoints } from '../lib/mapcats'
import { ApiError, api, errorText } from '../lib/api'
import { cell, fmt, table, titleCase } from '../lib/tables'
import '../styles/profile.css'

const PROV_LABEL = { gps: 'GPS from the report', exact: 'Matched by street names', fuzzy: 'Fuzzy name match',
  user: 'Placed by you', unmatched: 'Not placed yet (no coordinates)' }
const provLabel = (k) => PROV_LABEL[k] || (k.startsWith('jev') ? `Jev suggestion ${k.slice(3)}` : k)

function Src({ tid, n }) {
  return <span className="src" tabIndex={0} role="note" aria-label={`Source: table ${tid}`}
    title={`Table ${tid} · computed from ${fmt(n)} CCRS crash records`}>ⓘ</span>
}

function Kpis({ p }) {
  const n = cell(p, 'T1/crashes/value')
  const items = [
    ['Crashes', cell(p, p.kpis.crashes), `${cell(p, 'T1/years/value')} yr`],
    ['KSI', cell(p, p.kpis.ksi_crashes), 'fatal + serious'],
    ['Injury crashes', cell(p, p.kpis.injury_crashes), null],
    ['Per mile · year', cell(p, p.kpis.crashes_per_mi_yr), null],
  ]
  return (
    <div className="sf-kpis" aria-label="Key numbers">
      {items.map(([label, value, sub]) => (
        <div className="sf-kpi" key={label}>
          <div className="sf-kpi__label">{label} <Src tid="T1" n={n} /></div>
          <div className="sf-kpi__value">{fmt(value)}{sub ? <small>{sub}</small> : null}</div>
        </div>
      ))}
    </div>
  )
}

function Bars({ t }) {
  const max = Math.max(1, ...t.rows.map((r) => r.values.crashes))
  return (
    <div className="bars">
      {t.rows.map((r) => (
        <div className="bar" key={r.key}>
          <span className="lab">{r.label}</span>
          <span className="tr" aria-hidden="true">
            <i className="inj" style={{ width: `${(100 * r.values.injury_crashes) / max}%` }} />
            <i className="pdo" style={{ width: `${(100 * (r.values.crashes - r.values.injury_crashes)) / max}%` }} />
          </span>
          <span className="v mono">{fmt(r.values.crashes)}</span>
        </div>
      ))}
    </div>
  )
}

function Heat({ t }) {
  const hours = [...Array(24).keys()]
  const max = Math.max(1, ...t.rows.flatMap((r) => hours.map((h) => r.values[String(h)])))
  return (
    <div className="heat" role="table" aria-label="Crashes by hour and day">
      <span />
      {hours.map((h) => <span key={h} className="hh">{h % 6 === 0 ? h : ''}</span>)}
      {t.rows.map((r) => (
        <div className="hrow" role="row" key={r.key} style={{ display: 'contents' }}>
          <span className="lab" role="rowheader">{r.label.slice(0, 3)}</span>
          {hours.map((h) => {
            const v = r.values[String(h)]
            return <span key={h} role="cell" className="c" title={`${r.label} ${String(h).padStart(2, '0')}:00 · ${v}`}
              aria-label={`${r.label} ${h}:00, ${v}`}
              style={v ? { background: `color-mix(in srgb, var(--info) ${20 + (80 * v) / max}%, var(--surface-2))` } : undefined} />
          })}
        </div>
      ))}
    </div>
  )
}

// Rate against its critical rate: bar = rate, tick = critical rate, red when over. Scaled per kind (units differ).
function RateCell({ v, max }) {
  if (v.rate == null) return <td className="sf-num">—</td>
  const crit = v.critical_rate
  const over = v.over_critical === 'Yes'
  const pct = (x) => `${Math.min(100, (100 * x) / max)}%`
  return (
    <td title={`${fmt(v.rate)} ${v.rate_unit || ''}${crit != null ? ` · critical ${fmt(crit)} (95%)` : ''}`}>
      <div className="ratecell">
        <span className={`mono${over ? ' over' : ''}`}>{fmt(v.rate)}</span>
        {crit != null ? (
          <span className="rbar" aria-label={over ? 'over its critical rate' : 'under its critical rate'}>
            <i className={over ? 'over' : ''} style={{ width: pct(v.rate) }} />
            <b style={{ left: pct(crit) }} />
          </span>
        ) : null}
      </div>
    </td>
  )
}

function Locations({ t, onOpen }) {
  const hasRate = t.rows.some((r) => r.values.rate != null)
  const hasCrit = t.rows.some((r) => r.values.critical_rate != null)
  const maxBy = {}
  for (const r of t.rows) {
    const k = r.values.kind
    maxBy[k] = Math.max(maxBy[k] || 0, r.values.rate || 0, r.values.critical_rate || 0)
  }
  return (
    <div className="sf-table-wrap">
      <table className="sf-table">
        <thead>
          <tr><th>Location</th><th className="sf-num">Crashes</th><th className="sf-num">KSI</th>
            <th className="sf-num">Injury</th><th className="sf-num">Dark</th><th className="sf-num">Per yr</th>
            {hasRate ? <th className={hasCrit ? '' : 'sf-num'}>{hasCrit ? 'Rate vs critical' : 'Rate'}</th> : null}</tr>
        </thead>
        <tbody>
          {t.rows.map((r) => (
            <tr key={r.key} className={r.values.kind === 'segment' ? 'segrow' : ''}>
              <td><button type="button" className="rowlink" onClick={() => onOpen(r)}>{r.label}</button>
                {r.values.kind === 'segment' ? <span className="muted mono kind"> · {fmt(r.values.length_mi, 2)} mi</span> : null}</td>
              <td className="sf-num">{fmt(r.values.crashes)}</td>
              <td className="sf-num">{fmt(r.values.ksi_crashes)}</td>
              <td className="sf-num">{fmt(r.values.injury_crashes)}</td>
              <td className="sf-num">{fmt(r.values.dark_crashes)}</td>
              <td className="sf-num">{fmt(r.values.crashes_per_year)}</td>
              {hasRate ? (hasCrit ? <RateCell v={r.values} max={maxBy[r.values.kind] || 1} />
                : <td className="sf-num" title={r.values.rate_unit || ''}>{fmt(r.values.rate)}</td>) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function DataSources({ p, pull, onRefresh, busy }) {
  const prov = Object.entries(p.location_provenance || {}).filter(([, v]) => v)
  const cl = pull?.cleaning || {}
  return (
    <details className="adv sources">
      <summary>Where these crashes come from</summary>
      <div className="srcbody">
        <p className="muted">{p.source}. Pulled {pull?.pulled_at?.slice(0, 10)}.</p>
        <div className="lbl">Crash locations</div>
        <ul>{prov.map(([k, v]) => <li key={k}><span>{provLabel(k)}</span><span className="mono">{fmt(v)}</span></li>)}</ul>
        <div className="lbl">Cleaning</div>
        <ul>
          <li><span>Records read</span><span className="mono">{fmt(cl.rows_read)}</span></li>
          <li><span>Deleted by CHP, dropped</span><span className="mono">{fmt(cl.deleted_dropped)}</span></li>
          <li><span>Older report versions, dropped</span><span className="mono">{fmt(cl.duplicate_versions_dropped)}</span></li>
          <li><span>Preliminary, kept and flagged</span><span className="mono">{fmt(cl.preliminary_kept)}</span></li>
        </ul>
        <button type="button" className="sf-btn" onClick={onRefresh} disabled={busy}>Pull fresh data from CCRS</button>
      </div>
    </details>
  )
}

function Drill({ row, data, onClose }) {
  if (!data) return <div className="muted">Loading {row.label}…</div>
  const sev = table(data, `T3@${row.key}`)
  const types = table(data, `T4@${row.key}`)
  const light = table(data, `T6@${row.key}`)
  return (
    <div className="drill">
      <button type="button" className="linkbtn" onClick={onClose}>← All locations</button>
      <h2 className="h2">{row.label}</h2>
      <div className="muted mono">{fmt(row.values.crashes)} crashes · {fmt(row.values.ksi_crashes)} KSI · {fmt(row.values.crashes_per_year)} per year <Src tid="T2" n={row.values.crashes} /></div>
      <section><div className="sect-h"><h3 className="h3">Severity</h3><Src tid={sev.id} n={row.values.crashes} /></div>
        <ul className="kv">{sev.rows.filter((r) => r.values.crashes).map((r) => <li key={r.key}><span>{r.label}</span><span className="mono">{fmt(r.values.crashes)}</span></li>)}</ul></section>
      <section><div className="sect-h"><h3 className="h3">Collision type</h3><Src tid={types.id} n={row.values.crashes} /></div><Bars t={types} /></section>
      <section><div className="sect-h"><h3 className="h3">Lighting</h3><Src tid={light.id} n={row.values.crashes} /></div>
        <ul className="kv">{light.rows.map((r) => <li key={r.key}><span>{r.label}</span><span className="mono">{fmt(r.values.crashes)}</span></li>)}</ul></section>
      <section><h3 className="h3">Crash records</h3>
        <div className="sf-table-wrap"><table className="sf-table"><thead><tr><th>Date</th><th>Type</th><th>Sev.</th><th>Roads</th></tr></thead>
          <tbody>{data.crashes.map((c) => (
            <tr key={c.crash_id}><td className="mono">{c.date}{c.hour != null ? ` ${String(c.hour).padStart(2, '0')}h` : ''}</td>
              <td>{titleCase(c.collision_type)}</td><td className="mono">{c.severity}</td>
              <td className="muted">{c.primary_road} / {c.secondary_road}</td></tr>))}</tbody></table></div>
      </section>
    </div>
  )
}

// Crashes the profile counts (placed at a study location), with their location id.
function placedCrashes(crashes, asg) {
  const at = new Map((asg?.assignments || []).filter((a) => a.kind === 'intersection' || a.kind === 'segment')
    .map((a) => [a.crash_id, a.location_id]))
  return crashes.filter((c) => at.has(c.crash_id)).map((c) => ({ ...c, location_id: at.get(c.crash_id) }))
}

// Starts the CCRS pull in the background and polls its progress (#54): a 10-year pull is ~40 data.ca.gov calls,
// about a minute, so the screen says which step it is on instead of waiting on one frozen request.
async function pullCrashes(studyId, refresh, onStep, poll = 1000) {
  let r = await api(`/studies/${studyId}/crashes/pull?background=true${refresh ? '&refresh=true' : ''}`, { method: 'POST' })
  while (r && r.job) {
    onStep(r.job)
    await new Promise((res) => setTimeout(res, poll))
    const st = await api(`/studies/${studyId}/crashes/pull/status`)
    if (st.state === 'done') return st.summary
    if (st.state === 'error') throw new ApiError(st.status || 500, st.error)
    r = { job: st }
  }
  return r
}

// Step 3: crash profile dashboard. Every number shown comes from the C6 API response.
export default function Profile() {
  const { studyId } = useParams()
  const navigate = useNavigate()
  const [state, setState] = useState({ phase: 'loading' })
  const [drill, setDrill] = useState(null)       // { row, data }
  const [refreshing, setRefreshing] = useState(false)
  const [review, setReview] = useState(null)      // review list data while it's open (#97)
  const [picking, setPicking] = useState(null)    // { ids, done } while a map point is being picked

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const net = await api(`/studies/${studyId}/network`)
        if (!net.line) { if (alive) setState({ phase: 'nocorridor' }); return }
        if (alive) setState({ phase: 'pulling', line: net.line })
        const pull = await pullCrashes(studyId, false, (job) => alive && setState((s) => ({ ...s, job })))
        const [p, cr, asg] = await Promise.all([api(`/studies/${studyId}/profile`), api(`/studies/${studyId}/crashes`),
          api(`/studies/${studyId}/assignment`)])
        if (alive) setState({ phase: 'ready', line: net.line, net, pull, profile: p, crashes: placedCrashes(cr.crashes, asg) })
      } catch (e) {
        if (alive) setState((s) => ({ ...s, phase: 'error', error: errorText(e) }))
      }
    })()
    return () => { alive = false }
  }, [studyId])

  async function refresh() {
    setRefreshing(true)
    try {
      const pull = await pullCrashes(studyId, true, () => {})
      const [p, cr, asg] = await Promise.all([api(`/studies/${studyId}/profile`), api(`/studies/${studyId}/crashes`),
        api(`/studies/${studyId}/assignment`)])
      setState((s) => ({ ...s, pull, profile: p, crashes: placedCrashes(cr.crashes, asg) }))
      setDrill(null)
    } catch (e) {
      setState((s) => ({ ...s, refreshError: errorText(e) }))
    } finally { setRefreshing(false) }
  }

  async function reload() {
    const [p, cr, asg] = await Promise.all([api(`/studies/${studyId}/profile`), api(`/studies/${studyId}/crashes`),
      api(`/studies/${studyId}/assignment`)])
    setState((s) => ({ ...s, profile: p, crashes: placedCrashes(cr.crashes, asg) }))
  }

  async function openReview() {
    setDrill(null)
    setReview(await api(`/studies/${studyId}/review`))
  }

  async function reviewChanged(next) {           // a decision or an undo: the server recounts, the screen follows
    setReview(next)
    setPicking(null)
    await reload()
  }

  async function openLocation(row) {
    setDrill({ row, data: null })
    const data = await api(`/studies/${studyId}/profile/locations/${encodeURIComponent(row.key)}`)
    setDrill({ row, data })
  }

  const locs = useMemo(() => locationPoints(state.net), [state.net])
  const highlight = useMemo(() => (drill?.data ? new Set(drill.data.crashes.map((c) => c.crash_id)) : null), [drill])
  const p = state.profile

  return (
    <section className="profile" aria-label="Crash profile">
      <div className="mapcol">
        <ProfileMap line={state.line} crashes={state.crashes || []} locations={locs} highlight={highlight} selected={drill?.row.key}
          onPick={picking ? (pt) => picking.done(pt) : undefined} />
      </div>
      <div className="datacol">
        {state.phase === 'nocorridor' && (
          <div className="empty"><p>Draw the corridor first. The profile needs the study area.</p>
            <button type="button" className="sf-btn sf-btn--go" onClick={() => navigate(`/s/${studyId}/corridor`)}>Draw the corridor →</button></div>
        )}
        {(state.phase === 'loading' || state.phase === 'pulling') && (
          <div className="empty" role="status"><span className="sf-sig sf-sig--anim"><i /><i /><i /></span>
            <p>{state.phase === 'pulling' ? 'Pulling crashes from CCRS (data.ca.gov). The first pull for a corridor can take a minute.' : 'Loading…'}</p>
            {state.phase === 'pulling' && state.job?.step && state.job.step !== 'Starting' ? (
              <p className="muted mono">{state.job.step}{state.job.total ? ` · ${state.job.done + 1} of ${state.job.total}` : ''}</p>
            ) : null}</div>
        )}
        {state.phase === 'error' && <div className="err" role="alert">{state.error}</div>}
        {state.phase === 'ready' && p && (review ? (
          <ReviewList studyId={studyId} review={review} onChanged={reviewChanged} picking={picking} setPicking={setPicking}
            onClose={() => { setReview(null); setPicking(null) }} />
        ) : drill ? (
          <Drill row={drill.row} data={drill.data} onClose={() => setDrill(null)} />
        ) : (
          <>
            <Kpis p={p} />
            {cell(p, 'T1/unplaced/value') > 0 ? (
              <div className="note rv-entry">{fmt(cell(p, 'T1/unplaced/value'))} crash{cell(p, 'T1/unplaced/value') === 1 ? ' is' : 'es are'} not placed yet.
                {' '}<button type="button" className="linkbtn" onClick={openReview}>Review them →</button></div>
            ) : null}
            {p.caveats.length > 0 && (
              <ul className="caveats" aria-label="Caveats">
                {p.caveats.map((c) => <li key={c.key} className={c.limitation ? 'warn' : ''}>{c.text}</li>)}
              </ul>
            )}
            <section>
              <div className="sect-h"><h2 className="h3">Collision type</h2><Src tid="T4" n={cell(p, 'T1/crashes/value')} /></div>
              <Bars t={table(p, 'T4')} />
              <div className="legend small"><span><i style={{ background: 'var(--sev-i)' }} />Injury</span><span><i style={{ background: 'var(--sev-p)' }} />Property damage</span></div>
            </section>
            <section>
              <div className="sect-h"><h2 className="h3">When crashes happen</h2><Src tid="T9" n={cell(p, 'T1/crashes/value')} /></div>
              <Heat t={table(p, 'T9')} />
            </section>
            <section>
              <div className="sect-h"><h2 className="h3">Locations</h2><Src tid="T2" n={cell(p, 'T1/crashes/value')} /></div>
              <Locations t={table(p, 'T2')} onOpen={openLocation} />
            </section>
            <DataSources p={p} pull={state.pull} onRefresh={refresh} busy={refreshing} />
            {state.refreshError ? <div className="err" role="alert">{state.refreshError}</div> : null}
            <div className="cta-bar"><button type="button" className="sf-btn sf-btn--go" onClick={() => navigate(`/s/${studyId}/findings`)}>See findings →</button></div>
          </>
        ))}
      </div>
    </section>
  )
}
