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

// #270: the corridor-level answer first. The top locations from T2 in tab 3's ranking order (crashes, then KSI...),
// each with its numbers (T2 cells, cited) and the titles of its findings; a strip with the finding locations numbered
// F1...Fn; the findings counted by status. Built by code from these cells and templates, no AI.
const TOP = 5
function stationOf(net, lid) {
  const i = (net?.intersections || []).find((x) => x.id === lid)
  if (i?.station_ft != null) return i.station_ft
  const sg = (net?.segments || []).find((x) => x.id === lid)
  return sg ? (sg.from_station_ft + sg.to_station_ft) / 2 : null
}

function SummaryStrip({ net, marks, onOpen }) {
  const len = net?.length_ft || Math.max(1, ...marks.map((m) => m.at))
  const W = 560, PAD = 18, base = 34
  const x = (st) => PAD + (Math.max(0, Math.min(len, st)) / (len || 1)) * (W - 2 * PAD)
  return (
    <svg className="fsum-strip" viewBox={`0 0 ${W} 58`} role="img" aria-label="Finding locations along the corridor from A to B">
      <line x1={PAD} x2={W - PAD} y1={base} y2={base} className="strip-line" />
      <text x={PAD - 4} y={base + 4} textAnchor="end" className="strip-end">A</text>
      <text x={W - PAD + 4} y={base + 4} className="strip-end">B</text>
      {marks.map((m, k) => (
        <g key={m.lid} className="fmark" role="button" tabIndex={0} aria-label={`${m.labels.join(', ')}: ${m.name}`} data-testid="fmark"
          onClick={() => onOpen(m.first)} onKeyDown={(e) => { if (e.key === 'Enter') onOpen(m.first) }}>
          <title>{`${m.labels.join(', ')} · ${m.name}`}</title>
          <circle cx={x(m.at)} cy={base} r={9} />
          <text x={x(m.at)} y={base + 3.5} textAnchor="middle">{m.labels[0].slice(1)}</text>
          {k % 2 === 0 ? <text x={x(m.at)} y={12} textAnchor="middle" className="fmark-l">{m.labels.join(' ')}</text> : null}
        </g>
      ))}
    </svg>
  )
}

function Summary({ findings, profile, net, onOpen }) {
  const t2 = profile?.tables?.find((t) => t.id === 'T2')
  const live = findings.filter((f) => !f.stale)
  const n = {
    accepted: live.filter((f) => f.status === 'accepted').length,
    review: live.filter((f) => f.status !== 'accepted' && f.status !== 'rejected').length,
    rejected: live.filter((f) => f.status === 'rejected').length,
    stale: findings.length - live.length,
  }
  const byLoc = new Map()
  findings.forEach((f, i) => { if (!byLoc.has(f.location_id)) byLoc.set(f.location_id, []); byLoc.get(f.location_id).push(i) })
  // tab 3's default ranking (most crashes first, ties by name): the top TOP, plus every location with a finding
  const rows = t2 ? [...t2.rows].filter((r) => r.values.crashes > 0)
    .sort((a, b) => b.values.crashes - a.values.crashes || a.label.localeCompare(b.label)) : []
  const shown = rows.filter((r, k) => k < TOP || byLoc.has(r.key))
  const marks = [...byLoc.entries()].map(([lid, idx]) => ({ lid, first: idx[0], labels: idx.map((i) => `F${i + 1}`),
    name: locName(findings[idx[0]]), at: stationOf(net, lid) })).filter((m) => m.at != null)
  const src = (r, k) => <span className="src" role="note" tabIndex={0} aria-label={`Source: table T2, ${r.key} ${k}`}
    title={`Table T2 · ${r.label} · ${k}`}>ⓘ</span>
  return (
    <div className="fdetail fsummary" aria-label="Corridor summary">
      <div className="sf-eyebrow">Summary · {net?.corridor_name || 'the corridor'}</div>
      <h1 className="h2">Where to act first</h1>
      <p className="fsum-counts" data-testid="fsum-counts">
        {findings.length} finding{findings.length === 1 ? '' : 's'}: {n.accepted} accepted, {n.review} need{n.review === 1 ? 's' : ''} review, {n.rejected} rejected
        {n.stale ? `, ${n.stale} out of date` : ''}.</p>
      {marks.length ? <SummaryStrip net={net} marks={marks} onOpen={onOpen} /> : null}
      {shown.length ? (
        <ol className="fsum-list" aria-label="Top locations">
          {shown.map((r) => {
            const idx = byLoc.get(r.key) || []
            return (
              <li key={r.key} data-testid="fsum-row">
                <div className="fsum-head">
                  {idx.length ? <button type="button" className="rowlink" onClick={() => onOpen(idx[0])}>{r.label}</button> : <span>{r.label}</span>}
                  <span className="mono n" data-testid="fsum-crashes">{fmtNum(r.values.crashes)} crashes {src(r, 'crashes')}</span>
                  <span className="mono n">{fmtNum(r.values.ksi_crashes)} KSI {src(r, 'ksi_crashes')}</span>
                  <span className="mono n">{fmtNum(r.values.vru_crashes ?? 0)} ped/bike {src(r, 'vru_crashes')}</span>
                </div>
                {idx.length ? (
                  <ul className="fsum-f">{idx.map((i) => (
                    <li key={findings[i].id}><button type="button" className="linkbtn" onClick={() => onOpen(i)}>
                      <b className="mono">F{i + 1}</b> {shortTitle(findings[i])}</button> <Status s={findings[i].status} /></li>
                  ))}</ul>
                ) : <p className="muted small">No finding here: no crash type stands out.</p>}
              </li>
            )
          })}
        </ol>
      ) : <p className="muted">The location table (T2) isn&apos;t available.</p>}
      <p className="muted small">Order as on the crash profile: most crashes first. Findings are suggestions; only accepted ones go in the report.</p>
    </div>
  )
}

// Step 4. Findings from the over-representation screen (code, table T12). The AI analyst adds narrative later.
export default function Findings() {
  const { studyId } = useParams()
  const navigate = useNavigate()
  const { study } = useStudy()
  const [state, setState] = useState({ loading: true })
  const [sel, setSel] = useState(-1)              // -1: the corridor summary (#270), selected by default
  const [records, setRecords] = useState({})
  const [diagrams, setDiagrams] = useState({})

  useEffect(() => {
    let alive = true
    api(`/studies/${studyId}/findings/screen`, { method: 'POST' })
      .then(() => Promise.all([api(`/studies/${studyId}/findings`), api('/patterns'),
        api(`/studies/${studyId}/profile`).catch(() => null), api(`/studies/${studyId}/network`).catch(() => null)]))
      .then(([f, lib, profile, net]) => alive && setState({ findings: f.findings, lib, profile, net }))
      .catch((e) => alive && setState({ error: errorText(e) }))
    return () => { alive = false }
  }, [studyId])

  const findings = useMemo(() => state.findings || [], [state.findings])
  const cur = sel < 0 ? null : findings[Math.min(sel, Math.max(0, findings.length - 1))]
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
        <button type="button" data-testid="fsummary" className={`fcard fcard-sum${sel < 0 ? ' sel' : ''}`} onClick={() => setSel(-1)}
          aria-pressed={sel < 0}>
          <span className="loc-l">Corridor</span><span className="tt">Summary: where to act first</span>
        </button>
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
      {sel < 0 ? <Summary findings={findings} profile={state.profile} net={state.net} onOpen={setSel} /> : null}
      {cur && <Detail key={cur.id} f={cur} i={findings.indexOf(cur)} lib={state.lib} records={records[cur.id]} diagram={diagrams[cur.id]} study={study} onDecide={decide} />}
    </section>
  )
}
