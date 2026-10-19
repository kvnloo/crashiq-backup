import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, errorText } from '../lib/api'
import '../styles/findings.css'

// Step 4. Findings come from code first (#45): the HSM over-representation test finds which crash patterns
// stand out at each location, the pattern library adds possible factors and field checks, and the validator
// (C10) checks every number. The AI analyst (C9) will later rewrite the same findings in plainer prose.
export default function Findings() {
  const { studyId } = useParams()
  const navigate = useNavigate()
  const [state, setState] = useState({ loading: true })

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [config, f] = await Promise.all([api('/config'), api(`/studies/${studyId}/findings`)])
        let findings = f.findings
        let generated = null
        if (findings.length === 0) {     // first visit: find the patterns now (code only, no AI cost)
          generated = await api(`/studies/${studyId}/findings/generate`, { method: 'POST' })
          findings = generated.shown
        }
        if (alive) setState({ config, findings, rejected: f.rejected_count, generated })
      } catch (e) {
        if (alive) setState({ error: errorText(e) })
      }
    })()
    return () => { alive = false }
  }, [studyId])

  async function decide(id, status) {
    const f = await api(`/studies/${studyId}/findings/${encodeURIComponent(id)}?status=${status}`, { method: 'PATCH' })
    setState((s) => ({ ...s, findings: s.findings.map((x) => (x.id === id ? f : x)) }))
  }

  const { findings = [], error, loading } = state
  return (
    <section className="findings-screen" aria-label="Findings">
      <div className="fhead">
        <div className="sf-eyebrow">Findings</div>
        <h1 className="h2">Patterns behind the crashes</h1>
      </div>
      {loading ? <p className="muted">Loading…</p> : null}
      {error ? <div className="err" role="alert">{error}</div> : null}
      {!loading && !error && findings.length === 0 && (
        <div className="empty-state">
          <span className="sf-sig" data-s="g"><i /><i /><i /></span>
          <div>
            <h2 className="h3">No crash pattern stands out</h2>
            <p className="muted">
              No crash type, condition or severity is over-represented at any location compared with the corridor’s
              similar locations (HSM threshold-proportion test, 90% probability, at least two crashes). The crash
              profile is complete and ready to export.
            </p>
          </div>
        </div>
      )}
      {findings.length > 0 && (
        <ul className="flist">
          {findings.map((f) => (
            <li key={f.id} className={`fcard st-${f.status}`}>
              <p className="claim">{f.text}</p>
              <div className="meta mono">{f.pattern_ref || ''}</div>
              <div className="row">
                <button type="button" className="sf-btn sf-btn--go" disabled={f.status === 'accepted'} onClick={() => decide(f.id, 'accepted')}>Accept</button>
                <button type="button" className="sf-btn sf-btn--stop" disabled={f.status === 'rejected'} onClick={() => decide(f.id, 'rejected')}>Reject</button>
                <span className="muted status">{f.status}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
      <div className="cta-bar">
        <button type="button" className={`sf-btn${findings.length ? '' : ' sf-btn--go'}`} onClick={() => navigate(`/s/${studyId}/export`)}>
          Go to export →
        </button>
      </div>
    </section>
  )
}
