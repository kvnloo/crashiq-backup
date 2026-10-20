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
const RULE = { outside_buffer: 'outside the corridor buffer', outside_study_limits: 'beyond the study limits' }
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

// One place/exclude control row, for a single crash or a whole group
function Actions({ ids, review, suggestable, onDecide, onPick, label }) {
  const [mode, setMode] = useState(null)       // null | 'exclude' | 'intersection'
  const [reason, setReason] = useState('')
  const [loc, setLoc] = useState('')
  const n = ids.length
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
      <form className="rv-act" onSubmit={(e) => { e.preventDefault(); onDecide({ crash_ids: ids, action: 'place', method: 'intersection', location_id: loc }) }}>
        <select className="input" aria-label={`Intersection for ${label}`} value={loc} onChange={(e) => setLoc(e.target.value)} autoFocus>
          <option value="">Pick an intersection…</option>
          {review.intersections.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
        <button type="submit" className="sf-btn" disabled={!loc}>Place{n > 1 ? ` ${n}` : ''}</button>
        <button type="button" className="linkbtn" onClick={() => setMode(null)}>Cancel</button>
      </form>
    )
  }
  return (
    <div className="rv-act">
      {suggestable ? <button type="button" className="sf-btn" onClick={() => onDecide({ crash_ids: ids, action: 'place', method: 'suggestion' })}>
        At suggestion{n > 1 ? ` (${suggestable})` : ''}</button> : null}
      <button type="button" className="sf-btn" onClick={() => setMode('intersection')}>At an intersection</button>
      <button type="button" className="sf-btn" onClick={() => onPick(ids)}>On the map</button>
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
  const pick = (ids) => setPicking({ ids, done: (pt) => decide({ crash_ids: ids, action: 'place', method: 'map', ...pt }) })

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
      {review.groups.length === 0 ? <p className="muted">Nothing left to review.</p> : null}
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
              <span className="mono">{c.decision.action === 'place' ? `placed (${c.decision.method}) → ${landed(c.outcome)}` : `excluded: ${c.decision.reason}`}</span></li>
          ))}</ul></section>
      ) : null}
    </div>
  )
}
