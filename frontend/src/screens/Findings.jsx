import { Fragment, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import N10Diagram from '../components/N10Diagram'
import StripDiagram from '../components/StripDiagram'
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

// #267: a location by name, never an id (the server sends T2's label as location_name)
const ID_LIKE = /^(SEG|INT|LOC):|^osm-?\d/i
const locName = (f) => [f.location_name, f.meta?.location].find((x) => x && !ID_LIKE.test(String(x).trim())) || 'This location'
// the card's one line: the title without the trailing " at <location>" the card already shows; any other title
// (or a finding's text, when it has no title) stays whole and is ellipsised (PM review of #290)
const shortTitle = (f) => {
  const t = (f.title || f.text).trim()
  const tail = [f.location_name, f.meta?.location].filter(Boolean).map((x) => ` at ${x}`).find((x) => t.endsWith(x))
  return tail ? t.slice(0, -tail.length) : t
}
// the library entry by the finding's pattern, or by its reference when the pattern key is missing
const libEntry = (lib, f) => lib?.entries?.[f.meta?.pattern]
  || Object.values(lib?.entries || {}).find((e) => f.pattern_ref && e.ref === f.pattern_ref)

function Status({ s }) {
  if (s === 'accepted') return <span className="st acc">Accepted</span>
  if (s === 'rejected') return <span className="st rej">Rejected</span>
  return <span className="st">Needs review</span>
}

// #268: where a segment finding lies along the corridor, on the corridor strip (#102) with the segment marked and its
// end cross-streets labelled (PM review of #293); stations and names from the server
function StripPos({ s }) {
  return (
    <section aria-label="Where on the corridor">
      <div className="sect-h"><h3 className="h3">Where on the corridor</h3></div>
      <div data-testid="finding-strip">
        <StripDiagram crashes={s.crashes || []} intersections={s.intersections || []} lengthFt={s.length_ft}
          highlight={{ from_ft: s.from_ft, to_ft: s.to_ft, label: s.name || 'This segment' }} />
      </div>
      <p className="muted small-note">A segment has no intersection diagram; its crashes are the dots, and listed below.</p>
    </section>
  )
}

function Detail({ f, i, lib, records, diagram, study, onDecide }) {
  const [tab, setTab] = useState('records')
  const [play, setPlay] = useState(false)
  const entry = libEntry(lib, f)
  const segment = f.meta?.kind === 'segment'
  const m = f.meta || {}
  const own = !entry && Array.isArray(m.factors) && m.factors.length ? m.factors : null   // factors the finding carries
  return (
    <div className="fdetail">
      <div className="sf-eyebrow">F{i + 1} · {locName(f)}</div>
      {diagram?.kind === 'intersection' && diagram.diagram ? (
        <N10Diagram d={diagram.diagram} t={diagram.table} label={locName(f)}
          src={<span className="src" role="note" title={`The ${fmtNum(diagram.records)} crashes of this finding (records filter), table ${diagram.table.id}`}
            aria-label={`Source: this finding's ${diagram.records} crashes`}>ⓘ</span>} />
      ) : null}
      {diagram?.kind === 'segment' && diagram.strip?.from_ft != null ? <StripPos s={diagram.strip} /> : null}
      <button type="button" className="linkbtn" aria-expanded={play} onClick={() => setPlay(!play)}>
        {play ? 'Hide the pattern' : 'Play the pattern'}</button>
      {play ? <Replay anim={entry?.anim || 'generic'} segment={segment} records={records || []} /> : null}
      <Claim f={f} />
      <div className="why">
        <div>
          <span className="k">Pattern library{lib?.status === 'draft' && entry ? ' · draft' : ''}</span>
          <span>{entry ? entry.ref : own ? 'Factors from this finding' : 'No library entry for this crash type yet.'}</span>
        </div>
        <div>
          <span className="k">Possible contributing factors</span>
          <span>{entry ? entry.factors.join(' · ') : own ? own.join(' · ') : '—'}</span>
        </div>
        <div>
          <span className="k">Verify in the field</span>
          <span>{entry ? entry.verify : '—'}</span>
        </div>
      </div>
      <div>
        <div className="tabs" role="tablist">
          {[['records', `Records (${records ? records.length : '…'})`], ['audit', 'Audit']].map(([k, label]) => (
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
        <span className="muted mono small">{f.stale ? 'validator: out of date' : 'validator: all numbers traced ✓'}</span>
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
  const [diagrams, setDiagrams] = useState({})

  useEffect(() => {
    let alive = true
    api(`/studies/${studyId}/findings/screen`, { method: 'POST' })
      .then(() => Promise.all([api(`/studies/${studyId}/findings`), api('/patterns')]))
      .then(([f, lib]) => alive && setState({ findings: f.findings, lib }))
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

  useEffect(() => {
    if (!curId || diagrams[curId]) return undefined
    let alive = true
    api(`/studies/${studyId}/findings/${encodeURIComponent(curId)}/diagram`)
      .then((d) => alive && setDiagrams((s) => ({ ...s, [curId]: d })))
      .catch(() => alive && setDiagrams((s) => ({ ...s, [curId]: { kind: 'none' } })))
    return () => { alive = false }
  }, [curId, studyId, diagrams])

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
        {/* the server's order (#267): fatal, KSI, strength, crashes; stale ones last, under a divider */}
        {findings.map((f, i) => (
          <Fragment key={f.id}>
            {f.stale && !findings[i - 1]?.stale ? <div className="fdivider" role="separator">Out of date</div> : null}
            <button type="button" data-testid="fcard" className={`fcard${f === cur ? ' sel' : ''}`} onClick={() => setSel(i)}
              aria-pressed={f === cur} title={f.title || ''}>
              <span className="loc-l">{locName(f)}</span>
              <span className="tt">{shortTitle(f)}</span>
              <span className="meta"><Status s={f.status} /><span>{f.meta?.strength}</span>
                {f.rank?.fatal_crashes ? <span className="st fatal">Fatal crash</span> : null}
                {f.stale ? <span className="st rej" title={(f.stale_reasons || []).join('; ')}>Stale</span> : null}</span>
            </button>
          </Fragment>
        ))}
        <p className="muted small">Findings are suggestions. Only accepted findings go in the report.</p>
        <button type="button" className={`sf-btn${nAcc ? ' sf-btn--go' : ''}`} onClick={() => navigate(`/s/${studyId}/export`)}>Go to export →</button>
      </aside>
      {cur && <Detail key={cur.id} f={cur} i={findings.indexOf(cur)} lib={state.lib} records={records[cur.id]} diagram={diagrams[cur.id]} study={study} onDecide={decide} />}
    </section>
  )
}
