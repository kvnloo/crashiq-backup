import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, errorText } from '../lib/api'
import '../styles/findings.css'

// Step 4. Findings come from the AI analyst (C9) after the validator (C10) checks every number.
// Until the analyst is switched on, this screen says so plainly and lists any validated findings.
export default function Findings() {
  const { studyId } = useParams()
  const navigate = useNavigate()
  const [state, setState] = useState({ loading: true })

  useEffect(() => {
    let alive = true
    Promise.all([api('/config'), api(`/studies/${studyId}/findings`)])
      .then(([config, f]) => alive && setState({ config, findings: f.findings, rejected: f.rejected_count }))
      .catch((e) => alive && setState({ error: errorText(e) }))
    return () => { alive = false }
  }, [studyId])

  async function decide(id, status) {
    const f = await api(`/studies/${studyId}/findings/${encodeURIComponent(id)}?status=${status}`, { method: 'PATCH' })
    setState((s) => ({ ...s, findings: s.findings.map((x) => (x.id === id ? f : x)) }))
  }

  const { config, findings = [], error, loading } = state
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
          <span className="sf-sig" data-s={config?.ai?.claude_configured ? 'y' : 'r'}><i /><i /><i /></span>
          <div>
            <h2 className="h3">{config?.ai?.claude_configured ? 'No findings yet' : 'The AI analyst isn’t switched on yet'}</h2>
            <p className="muted">
              {config?.ai?.claude_configured
                ? 'The analyst hasn’t written findings for this study.'
                : 'Findings need an Anthropic API key on the server. Until then, the crash profile is complete and ready to export.'}
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
