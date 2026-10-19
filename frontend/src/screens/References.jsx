import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import TopBar from '../components/TopBar'
import { api, errorText } from '../lib/api'
import '../styles/references.css'

const STATUS = {
  follows: { label: 'Follows the source', s: 'g' },
  decision: { label: 'Engineer decision open', s: 'y' },
  planned: { label: 'Not built yet', s: 'r' },
}

// Methods & references: every method CrashIQ uses, the source it follows, and what is still open.
export default function References() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    let alive = true
    api('/references').then((d) => alive && setData(d)).catch((e) => alive && setErr(errorText(e)))
    return () => { alive = false }
  }, [])

  const src = data?.sources || {}
  const order = []
  for (const m of data?.methods || []) for (const [k] of m.cite) if (!order.includes(k)) order.push(k)
  const num = (k) => order.indexOf(k) + 1

  return (
    <>
      <TopBar />
      <main className="refs" aria-label="Methods and references">
        <div className="sf-eyebrow">Methods &amp; references</div>
        <h1 className="h2">How CrashIQ computes each number, and the source it follows</h1>
        {data && <p className="muted lead">{data.note} Updated {data.updated}.</p>}
        {err && <div className="err" role="alert">{err}</div>}
        {data && (
          <>
            <ol className="methods">
              {data.methods.map((m) => (
                <li key={m.topic} className="method">
                  <div className="mhead">
                    <h2 className="h3">{m.topic}</h2>
                    <span className="mstatus"><span className="sf-sig" data-s={STATUS[m.status].s} aria-hidden="true"><i /><i /><i /></span>
                      {STATUS[m.status].label}</span>
                  </div>
                  <p>{m.what}</p>
                  <ul className="cites">
                    {m.cite.map(([k, where]) => (
                      <li key={k + where}><a href={`#ref-${k}`} className="mono">[{num(k)}]</a> {src[k].publisher}, <i>{src[k].title}</i>{where ? ` — ${where}` : ''}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
            <h2 className="h3 srch">Sources</h2>
            <ol className="sources">
              {order.map((k) => (
                <li key={k} id={`ref-${k}`}>
                  <span className="mono">[{num(k)}]</span> {src[k].publisher}, <i>{src[k].title}</i>.{' '}
                  <a href={src[k].url} target="_blank" rel="noreferrer">{src[k].url.replace(/^https?:\/\//, '')}</a>
                </li>
              ))}
            </ol>
          </>
        )}
        <p><Link to="/">← Back to CrashIQ</Link></p>
      </main>
    </>
  )
}
