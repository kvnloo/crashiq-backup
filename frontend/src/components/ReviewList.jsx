// C11 review list (#97): crashes the app couldn't place, grouped by street pair. The engineer chooses a location
// (the locator's suggestion, a study intersection, or a point on the map) or excludes with a reason; the server
// does every count. Decisions are undoable and survive a re-pull.
import { useState } from 'react'
import { api, errorText } from '../lib/api'
import { fmt } from '../lib/tables'

const REASON = {
  no_cross_street: 'No cross street in the report',
  no_coordinates: 'No GPS, and no exact street match',
  report_changed: 'CHP revised the report: check again',
}
const SEV = { K: 'Fatal', A: 'Serious', B: 'Minor', C: 'Possible', U: 'Injury', O: 'Property' }

// what the code did with a placement: counted at a location, or excluded by the normal rules (e.g. off the buffer)
const RULE = { outside_buffer: 'outside the corridor buffer', outside_study_limits: 'beyond the study limits',
  fars_off_corridor: 'FARS places it elsewhere on its roads' }
function landed(o) {
  if (!o) return '—'
  if (o.kind === 'intersection' || o.kind === 'segment') return o.location || o.kind
  if (o.kind === 'excluded') return `not counted: ${RULE[o.rule] || o.rule}`
  return o.kind || '—'
}

function where(c) {
  const off = c.offset_ft ? ` · ${fmt(Math.round(c.offset_ft))} ft ${c.offset_dir || ''}`.trimEnd() : ''
  return `${c.primary_road || '—'} / ${c.secondary_road || '—'}${off}`
}

// One place/exclude control row, for a single crash or a whole group. A fatal crash can only be placed with a
// source for its location (#175): the field comes first and every place button waits for it.
function Actions({ ids, review, suggestable, onDecide, onPick, label, needSource = false }) {
  const [mode, setMode] = useState(null)       // null | 'exclude' | 'intersection'
  const [reason, setReason] = useState('')
  const [loc, setLoc] = useState('')
  const [source, setSource] = useState('')
  const n = ids.length
  const src = source.trim()
  const blocked = needSource && !src
  const withSource = (body) => (needSource ? { ...body, source: src } : body)
  const sourceField = needSource ? (
    <input className="input rv-source" aria-label={`Source for ${label}`} placeholder="Source for the location (link or note), required"
      value={source} onChange={(e) => setSource(e.target.value)} maxLength={500} />
  ) : null
  if (mode === 'exclude') {
    return (
      <form className="rv-act" onSubmit={(e) => { e.preventDefault(); onDecide({ crash_ids: ids, action: 'exclude', reason }) }}>
        <input className="input" aria-label={`Why exclude ${label}`} placeholder="Why? e.g. parking lot, not the road"
          value={reason} onChange={(e) => setReason(e.target.value)} maxLength={200} autoFocus />
        <button type="submit" className="sf-btn" disabled={!reason.trim()}>Exclude{n > 1 ? ` ${n}` : ''}</button>
        <button type="button" className="linkbtn" onClick={() => setMode(null)}>Cancel</button>
      </form>
    )
  }
  if (mode === 'intersection') {
    return (
      <form className="rv-act" onSubmit={(e) => { e.preventDefault(); onDecide(withSource({ crash_ids: ids, action: 'place', method: 'intersection', location_id: loc })) }}>
        {sourceField}
        <select className="input" aria-label={`Intersection for ${label}`} value={loc} onChange={(e) => setLoc(e.target.value)} autoFocus>
          <option value="">Pick an intersection…</option>
          {review.intersections.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
        <button type="submit" className="sf-btn" disabled={!loc || blocked}>Place{n > 1 ? ` ${n}` : ''}</button>
        <button type="button" className="linkbtn" onClick={() => setMode(null)}>Cancel</button>
      </form>
    )
  }
  return (
    <div className="rv-act">
      {sourceField}
      {suggestable ? <button type="button" className="sf-btn" disabled={blocked} onClick={() => onDecide(withSource({ crash_ids: ids, action: 'place', method: 'suggestion' }))}>
        At suggestion{n > 1 ? ` (${suggestable})` : ''}</button> : null}
      <button type="button" className="sf-btn" disabled={blocked} onClick={() => setMode('intersection')}>At an intersection</button>
      <button type="button" className="sf-btn" disabled={blocked} onClick={() => onPick(ids, needSource ? src : null)}>On the map</button>
      <button type="button" className="sf-btn" onClick={() => setMode('exclude')}>Exclude</button>
    </div>
  )
}

export default function ReviewList({ studyId, review, onChanged, onClose, picking, setPicking }) {
  const [open, setOpen] = useState(null)      // expanded group key
  const [err, setErr] = useState('')

  async function decide(body) {
    setErr('')
    try {
      const r = await api(`/studies/${studyId}/review/decisions`, { method: 'POST', body })
      onChanged(r.review)
    } catch (e) { setErr(errorText(e)) }
  }
  async function undo() {
    setErr('')
    try { onChanged((await api(`/studies/${studyId}/review/undo`, { method: 'POST' })).review) } catch (e) { setErr(errorText(e)) }
  }
  const pick = (ids, source) => setPicking({ ids, done: (pt) => decide({ crash_ids: ids, action: 'place', method: 'map', ...pt, ...(source ? { source } : {}) }) })

  return (
    <div className="drill review" aria-label="Review list">
      <button type="button" className="linkbtn" onClick={onClose}>← Crash profile</button>
      <div className="sect-h">
        <h2 className="h2">Review list</h2>
        <button type="button" className="linkbtn" onClick={undo} disabled={!review.can_undo}>Undo last</button>
      </div>
      <p className="muted">{fmt(review.open)} crash{review.open === 1 ? '' : 'es'} the app couldn't place. Choose where each one happened, or exclude it with a reason. Every count is still computed from the location you choose.</p>
      {picking ? <div className="note" role="status">Click the map where {picking.ids.length > 1 ? `these ${picking.ids.length} crashes` : 'the crash'} happened. <button type="button" className="linkbtn" onClick={() => setPicking(null)}>Cancel</button></div> : null}
      {err ? <div className="err" role="alert">{err}</div> : null}
      {review.groups.length === 0 && !review.fatal_open ? <p className="muted">Nothing left to review.</p> : null}
      {review.fatal_open ? (
        <section className="rv-fatal" aria-label="Fatal crashes without a location">
          <h3 className="h3 rv-fatal-h" data-testid="fatal-header"><span className="flag" aria-hidden="true">⚑</span>
            {fmt(review.fatal_open)} fatal crash{review.fatal_open === 1 ? '' : 'es'} need{review.fatal_open === 1 ? 's' : ''} a location</h3>
          <p className="muted small-note">Every fatal crash should be placed. Look up where it happened (the searches open in your browser), place it, and cite the source.</p>
          <ul className="rv-crashes">
            {review.fatal.map((c) => (
              <li key={c.crash_id} className="rv-fatal-item" data-testid="fatal-item">
                <div className="mono"><span className="flag" aria-hidden="true">⚑</span> {c.date}{c.hour != null ? ` ${String(c.hour).padStart(2, '0')}h` : ''} · Fatal{c.killed > 1 ? ` (${c.killed} killed)` : ''} · {c.collision_type || 'Crash'}{c.city ? ` · ${c.city}` : ''}</div>
                <div className="muted">{where(c)} · {REASON[c.reason] || c.reason}{c.suggestion ? ` · suggested: ${c.suggestion.tier}` : ''}</div>
                {c.fars_hint ? <div className="muted" data-testid="fars-hint">FARS puts this crash {fmt(c.fars_hint.miles_from_corridor)} mi from the corridor (case {c.fars_hint.fars_case}), but the map doesn't show both roads the report names there. Check it before placing.</div> : null}
                <div className="rv-lookup">Look up: {c.lookup.map((l) => <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer">{l.label}</a>)}</div>
                <Actions ids={[c.crash_id]} review={review} suggestable={c.suggestion ? 1 : 0} onDecide={decide} onPick={pick} label={`fatal crash ${c.crash_id}`} needSource />
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <ul className="rv-groups">
        {review.groups.map((g) => (
          <li key={g.key} className="rv-group">
            <button type="button" className="rv-head" aria-expanded={open === g.key} onClick={() => setOpen(open === g.key ? null : g.key)}>
              <span className="mono">{g.key}</span><span className="mono">{fmt(g.count)}</span>
            </button>
            <div className="muted rv-why">{Object.entries(g.reasons).map(([k, v]) => `${REASON[k] || k}${g.count > 1 ? ` (${v})` : ''}`).join(' · ')}</div>
            {g.count > 1 ? <Actions ids={g.crashes.map((c) => c.crash_id)} review={review} suggestable={g.with_suggestion}
              onDecide={decide} onPick={pick} label={`all ${g.count} crashes at ${g.key}`} /> : null}
            {open === g.key || g.count === 1 ? (
              <ul className="rv-crashes">
                {g.crashes.map((c) => (
                  <li key={c.crash_id}>
                    <div className="mono">{c.date}{c.hour != null ? ` ${String(c.hour).padStart(2, '0')}h` : ''} · {SEV[c.severity] || c.severity || '—'} · {c.collision_type || 'Crash'}</div>
                    <div className="muted">{where(c)}{c.suggestion ? ` · suggested: ${c.suggestion.tier}` : ''}</div>
                    <Actions ids={[c.crash_id]} review={review} suggestable={c.suggestion ? 1 : 0} onDecide={decide} onPick={pick} label={`crash ${c.crash_id}`} />
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ul>
      {review.decided.length ? (
        <section><h3 className="h3">Decided ({fmt(review.decided.length)})</h3>
          <ul className="kv">{review.decided.map((c) => (
            <li key={c.crash_id}><span>{where(c)}</span>
              <span className="mono">{c.decision.action === 'place' ? `placed (${c.decision.method}) → ${landed(c.outcome)}${c.decision.source ? ` · source: ${c.decision.source}` : ''}` : `excluded: ${c.decision.reason}`}</span></li>
          ))}</ul></section>
      ) : null}
    </div>
  )
}
