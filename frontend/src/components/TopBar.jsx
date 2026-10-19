import { Link } from 'react-router-dom'

// Static logo + name + current project (docs/05-ui-review.md header rows: no theme toggle, no example badge).
export default function TopBar({ projectName }) {
  return (
    <header className="top">
      <Link to="/" className="brand" aria-label="CrashIQ home">
        <span className="sf-sig" data-s="g" aria-hidden="true"><i /><i /><i /></span>
        <span>Crash<b>IQ</b></span>
      </Link>
      {projectName ? <div className="proj" title={projectName}>{projectName}</div> : null}
      <Link to="/methods" className="toplink">Methods &amp; references</Link>
    </header>
  )
}
