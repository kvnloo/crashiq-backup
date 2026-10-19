import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, errorText } from '../lib/api'
import { cell, fmt, table } from '../lib/tables'
import { useStudy } from '../study'
import '../styles/export.css'

const FILES = [
  { key: 'pdf', label: 'PDF report', desc: 'Crash profile for the safety section: summary, locations, severity, collision types, factors, caveats and sources.' },
  { key: 'xlsx', label: 'Excel workbook', desc: 'Every table behind the profile, one sheet each (T1 Summary … T12 Over-represented crash types), plus a study sheet.' },
]

// Thumbnail previews of the report, filled from the profile so they show the real numbers.
function Pages({ p, study }) {
  const t2 = table(p, 'T2')
  const t4 = table(p, 'T4')
  return (
    <div className="pages" aria-hidden="true">
      <div className="page">
        <h4>{study?.name}: crash profile</h4>
        <div className="kp">
          {Object.values(p.kpis).map((a) => <span key={a}><b>{fmt(cell(p, a))}</b></span>)}
        </div>
        <div className="ln" /><div className="ln" style={{ width: '70%' }} />
        <table><tbody>{table(p, 'T1').rows.slice(0, 8).map((r) => <tr key={r.key}><td>{r.label}</td><td>{fmt(r.values.value)}</td></tr>)}</tbody></table>
      </div>
      <div className="page">
        <h4>Locations</h4>
        <table><tbody>{t2.rows.slice(0, 14).map((r) => <tr key={r.key}><td>{r.label}</td><td>{fmt(r.values.crashes)}</td></tr>)}</tbody></table>
      </div>
      <div className="page">
        <h4>Collision type</h4>
        <table><tbody>{t4.rows.map((r) => <tr key={r.key}><td>{r.label}</td><td>{fmt(r.values.crashes)}</td></tr>)}</tbody></table>
        <div className="ln" /><div className="ln" style={{ width: '60%' }} />
      </div>
    </div>
  )
}

// Step 5: one primary action, downloads the chosen files.
export default function Export() {
  const { studyId } = useParams()
  const { study } = useStudy()
  const [p, setP] = useState(null)
  const [err, setErr] = useState('')
  const [pick, setPick] = useState({ pdf: true, xlsx: true })

  useEffect(() => {
    let alive = true
    api(`/studies/${studyId}/profile`).then((x) => alive && setP(x)).catch((e) => alive && setErr(errorText(e)))
    return () => { alive = false }
  }, [studyId])

  const n = FILES.filter((f) => pick[f.key]).length

  function download() {
    for (const f of FILES) {
      if (!pick[f.key]) continue
      const a = document.createElement('a')
      a.href = `/api/studies/${studyId}/export.${f.key}`
      a.download = ''
      document.body.appendChild(a)
      a.click()
      a.remove()
    }
  }

  return (
    <section className="export" aria-label="Export">
      <div>
        <div className="sf-eyebrow">Export</div>
        <h1 className="h1">Ready for the<br />safety section.</h1>
        {p ? <Pages p={p} study={study} /> : <p className="muted">{err || 'Loading the profile…'}</p>}
      </div>
      <div className="opts">
        {FILES.map((f) => (
          <label className="opt" key={f.key}>
            <input type="checkbox" checked={pick[f.key]} onChange={(e) => setPick((s) => ({ ...s, [f.key]: e.target.checked }))} />
            <div><div className="h3">{f.label}</div><div className="muted desc">{f.desc}</div></div>
          </label>
        ))}
        {p?.caveats?.length ? (
          <div className="muted note-list">The report lists {p.caveats.length} caveat{p.caveats.length === 1 ? '' : 's'} with the data.</div>
        ) : null}
        <div className="muted note-list">The PDF includes a method statement and its references (<Link to="/methods">Methods &amp; references</Link>).</div>
        <div className="cta-bar">
          <button type="button" className="sf-btn sf-btn--go" disabled={!p || n === 0} onClick={download}>
            {n === 0 ? 'Choose a file' : `Export ${n} file${n === 1 ? '' : 's'} ↓`}
          </button>
        </div>
      </div>
    </section>
  )
}
