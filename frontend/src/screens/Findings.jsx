import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import CollisionDiagram from '../components/CollisionDiagram'
import Replay from '../components/Replay'
import { api, errorText } from '../lib/api'
import { fmtNum } from '../lib/tables'
import { useStudy } from '../study'
import '../styles/findings.css'

const SEV_LABEL = { K: 'Fatal', A: 'Serious injury', B: 'Minor injury', C: 'Possible injury', U: 'Injury', O: 'PDO' }
const NUM = /(?<![\w.])\d+(?:\.\d+)?%?(?![\w])/g

// Claim text with every number marked and traced to the table cell it came from.
function Claim({ f }) {
  const parts = []
  let last = 0
  for (const m of f.text.matchAll(NUM)) {
    const raw = m[0].replace('%', '')
    const n = f.numbers.find((x) => fmtNum(x.value) === raw)
    parts.push(f.text.slice(last, m.index))
    parts.push(n
      ? <span key={m.index} className="num" title={`From table ${n.table_id}, cell ${n.cell}`}>{m[0]}</span>
      : m[0])
    last = m.index + m[0].length
  }
  parts.push(f.text.slice(last))
  return <p className="claim">{parts}</p>
}

function Status({ s }) {
  if (s === 'accepted') return <span className="st acc">Accepted</span>
  if (s === 'rejected') return <span className="st rej">Rejected</span>
  return <span className="st">Needs review</span>
}

function Detail({ f, i, lib, records, corridor, study, onDecide }) {
  const [tab, setTab] = useState('records')
  const entry = lib?.entries?.[f.meta?.pattern]
  const segment = f.meta?.kind === 'segment'
  const m = f.meta || {}
  return (
    <div className="fdetail">
      <div className="sf-eyebrow">F{i + 1} · {m.location || f.location_id}</div>
      <Replay anim={entry?.anim || 'generic'} segment={segment} records={records || []} />
      <Claim f={f} />
      <div className="why">
        <div>
          <span className="k">Pattern library{lib?.status === 'draft' && entry ? ' · draft' : ''}</span>
          <span>{entry ? entry.ref : 'No library entry for this crash type yet.'}</span>
        </div>
        <div>
          <span className="k">Possible contributing factors</span>
          <span>{entry ? entry.factors.join(' · ') : '—'}</span>
        </div>
        <div>
          <span className="k">Verify in the field</span>
          <span>{entry ? entry.verify : '—'}</span>
        </div>
      </div>
      <div>
        <div className="tabs" role="tablist">
          {[['records', `Records (${records ? records.length : '…'})`], ['diagram', 'Collision diagram'], ['audit', 'Audit']].map(([k, label]) => (
            <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{label}</button>
          ))}
        </div>
        <div className="tabbody">
          {tab === 'records' && (
            <div className="sf-table-wrap">
              <table className="sf-table">
                <thead><tr><th>Date</th><th className="sf-num">Hour</th><th>Type</th><th>Severity</th><th>Lighting</th><th>As written in CCRS</th></tr></thead>
                <tbody>
                  {(records || []).map((c) => (
                    <tr key={c.crash_id}>
                      <td className="mono">{c.date}</td>
                      <td className="sf-num">{c.hour != null ? `${String(c.hour).padStart(2, '0')}:00` : '—'}</td>
                      <td>{(c.collision_type || '—').toLowerCase()}</td>
                      <td>{SEV_LABEL[c.severity] || c.severity}</td>
                      <td>{(c.lighting || '—').toLowerCase()}</td>
                      <td className="mono muted small">{[c.primary_road, c.secondary_road].filter(Boolean).join(' / ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {tab === 'diagram' && (
            <div className="card-pad">
              <CollisionDiagram records={records || []} corridor={corridor} cross={m.location} segment={segment} />
            </div>
          )}
          {tab === 'audit' && (
            <dl className="card-pad audit">
              <dt>Data</dt><dd>CCRS {study?.from_year}–{study?.to_year} · {m.corridor_crashes ?? '—'} crashes placed on the corridor</dd>
              <dt>Assignment</dt><dd>{study?.radius_ft ?? 250} ft intersection influence area; {study?.buffer_ft ?? 100} ft corridor buffer</dd>
              <dt>Test</dt><dd>Excess proportion of specific crash types (HSM Part B screening), compared with the {m.reference || 'corridor locations'}. {m.method}.</dd>
              <dt>Result</dt><dd>{String(m.method || '').startsWith('Binomial') ? 'Binomial confidence' : 'P(true share > reference share)'} = {m.probability} · {m.strength} · excess {m.excess_pct} points</dd>
              <dt>Numbers</dt><dd>{f.numbers.map((n) => `${n.table_id}/${n.cell}`).join(' · ')}</dd>
              <dt>Written by</dt><dd>{f.source === 'screen' ? 'Code, from table T12 (no AI)' : 'AI analyst; every number checked by the validator'}</dd>
              <dt>Caveats</dt><dd>Small numbers; regression to the mean; police-reported crashes only, so injury counts are a lower bound.</dd>
            </dl>
          )}
        </div>
      </div>
      {f.stale && (
        <div className="err" role="alert">This finding no longer matches the data (the study changed since it was written), so it
          can’t be accepted and won’t be exported.</div>
      )}
      <div className="decide">
        <button type="button" className="sf-btn sf-btn--go" disabled={f.status === 'accepted' || f.stale} onClick={() => onDecide(f.id, 'accepted')}>✓ Accept</button>
        <button type="button" className="sf-btn sf-btn--stop" disabled={f.status === 'rejected'} onClick={() => onDecide(f.id, 'rejected')}>✗ Reject</button>
        <span className="sp" />
        <span className="muted mono small">validator: all numbers traced ✓</span>
      </div>
    </div>
  )
}

// Step 4. Findings from the over-representation screen (code, table T12). The AI analyst adds narrative later.
export default function Findings() {
  const { studyId } = useParams()
  const navigate = useNavigate()
  const { study } = useStudy()
  const [state, setState] = useState({ loading: true })
  const [sel, setSel] = useState(0)
  const [records, setRecords] = useState({})

  useEffect(() => {
    let alive = true
    api(`/studies/${studyId}/findings/screen`, { method: 'POST' })
      .then(() => Promise.all([api(`/studies/${studyId}/findings`), api('/patterns'),
        api(`/studies/${studyId}/network`).catch(() => null)]))
      .then(([f, lib, net]) => alive && setState({ findings: f.findings, lib, corridor: net?.corridor_name || 'Corridor' }))
      .catch((e) => alive && setState({ error: errorText(e) }))
    return () => { alive = false }
  }, [studyId])

  const findings = useMemo(() => state.findings || [], [state.findings])
  const cur = findings[Math.min(sel, Math.max(0, findings.length - 1))]
  const curId = cur?.id

  useEffect(() => {
    if (!curId || records[curId]) return undefined
    let alive = true
    api(`/studies/${studyId}/findings/${encodeURIComponent(curId)}/records`)
      .then((r) => alive && setRecords((s) => ({ ...s, [curId]: r.records })))
      .catch(() => alive && setRecords((s) => ({ ...s, [curId]: [] })))
    return () => { alive = false }
  }, [curId, studyId, records])

  async function decide(id, status) {
    const f = await api(`/studies/${studyId}/findings/${encodeURIComponent(id)}?status=${status}`, { method: 'PATCH' })
    setState((s) => ({ ...s, findings: s.findings.map((x) => (x.id === id ? f : x)) }))
  }

  const nAcc = findings.filter((f) => f.status === 'accepted').length
  if (state.loading) return <section className="findings-screen pad" aria-label="Findings"><p className="muted">Screening every location…</p></section>
  if (state.error) return <section className="findings-screen pad" aria-label="Findings"><div className="err" role="alert">{state.error}</div></section>

  if (!findings.length) {
    return (
      <section className="findings-screen pad" aria-label="Findings">
        <div className="sf-eyebrow">Findings</div>
        <h1 className="h2">No crash type stands out</h1>
        <div className="empty-state">
          <span className="sf-sig" data-s="g"><i /><i /><i /></span>
          <p className="muted">Every location was screened against the corridor as a whole. None has a crash type whose share is high enough,
            with enough crashes, to be more than chance (table T12 in the Excel export lists the test).</p>
        </div>
        <div className="cta-bar"><button type="button" className="sf-btn sf-btn--go" onClick={() => navigate(`/s/${studyId}/export`)}>Go to export →</button></div>
      </section>
    )
  }

  return (
    <section className="findings-screen" aria-label="Findings">
      <aside className="flist" aria-label="Findings list">
        <div className="sf-eyebrow">{findings.length} findings · {nAcc} accepted</div>
        {findings.map((f, i) => (
          <button key={f.id} type="button" className={`fcard${f === cur ? ' sel' : ''}`} onClick={() => setSel(i)} aria-pressed={f === cur}>
            <span className="loc-l">{f.meta?.location || f.location_id}</span>
            <span className="tt">{f.title || f.text}</span>
            <span className="meta"><Status s={f.status} /><span>{f.meta?.strength}</span>
              {f.stale ? <span className="st rej" title={(f.stale_reasons || []).join('; ')}>Stale</span> : null}</span>
          </button>
        ))}
        <p className="muted small">Findings are suggestions. Only accepted findings go in the report.</p>
        <button type="button" className={`sf-btn${nAcc ? ' sf-btn--go' : ''}`} onClick={() => navigate(`/s/${studyId}/export`)}>Go to export →</button>
      </aside>
      {cur && <Detail key={cur.id} f={cur} i={findings.indexOf(cur)} lib={state.lib} records={records[cur.id]}
        corridor={state.corridor} study={study} onDecide={decide} />}
    </section>
  )
}
