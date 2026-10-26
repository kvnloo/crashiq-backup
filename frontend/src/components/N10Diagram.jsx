// G. Collision diagram (#106, N10): drawn from the backend's steps; the numbers key to T21 (date order). Shared by
// the tab 3 location drill-in and a finding's diagram (#268); `src` is the caller's source mark.
import IntersectionDiagram from './IntersectionDiagram'
import { fmt } from '../lib/tables'
import '../styles/diagram.css'

function LegendIcon({ steps }) {
  return <svg viewBox="0 0 48 48" width="36" height="36" aria-hidden="true"><IntersectionDiagram.Steps steps={steps} /></svg>
}

export default function N10Diagram({ d, t, label, src = null }) {
  const nd = d.not_drawn || {}
  const notes = [nd.no_party_data ? `${fmt(nd.no_party_data)} with no party data for their year in this pull, so no direction of travel` : null,
    nd.no_direction ? `${fmt(nd.no_direction)} with no direction of travel in the report` : null,
    nd.no_room ? `${fmt(nd.no_room)} more than the diagram has room for on their approach` : null].filter(Boolean)
  return (
    <section aria-label="Collision diagram">
      <div className="sect-h"><h3 className="h3">Collision diagram</h3>{src}</div>
      <IntersectionDiagram diagram={d} label={label} />
      {notes.length ? <p className="muted small-note">Not drawn, listed below: {notes.join('; ')}.</p> : null}
      <div className="cdiag-legend">
        {[...d.legend.symbols, ...d.legend.marks].map((x) => <span key={x.key}><LegendIcon steps={x.steps} />{x.label}</span>)}
      </div>
      {t ? <details className="showtable"><summary>Crash list (numbers on the diagram)</summary>
        <div className="sf-table-wrap"><table className="sf-table"><thead><tr><th>#</th><th>Date, time</th><th>Approach</th><th>Type</th><th>Sev.</th><th title="Road surface + light (HSM): C dry, W wet, S snow/ice, O other · D day, N dark without street lights, L dark with street lights">Code</th></tr></thead>
          <tbody>{t.rows.map((r) => <tr key={r.key}><td className="mono">{r.key}</td><td className="mono">{r.label}</td><td className="mono">{r.values.approach}</td>
            <td>{r.values.type}</td><td className="mono">{r.values.severity}</td><td className="mono">{r.values.code}</td></tr>)}</tbody></table></div>
        <p className="muted small-note">Code = road surface + light (HSM): C dry, W wet, S snow/ice, O other · D daylight, N dark without street lights, L dark with street lights.</p>
      </details> : null}
    </section>
  )
}
