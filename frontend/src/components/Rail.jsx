import { NavLink } from 'react-router-dom'
import { STEPS, stepPath } from '../steps'

// Left rail: the five steps. Steps after Setup open once a study exists (they need its id).
// `reached` = index of the furthest step the study has data for; earlier steps show a check.
export default function Rail({ studyId, current, reached = 0 }) {
  return (
    <nav className="rail" aria-label="Study steps">
      <div className="sf-eyebrow">Safety study</div>
      {STEPS.map((s, i) => {
        const done = i < current && i <= reached
        const open = i === 0 || Boolean(studyId)
        const cls = `step${i === current ? ' on' : ''}${done ? ' done' : ''}${open ? '' : ' locked'}`
        const body = (
          <>
            <span className="lamp" aria-hidden="true">{done ? '✓' : i + 1}</span>
            <span className="t">{s.label}</span>
          </>
        )
        return open ? (
          <NavLink key={s.key} to={stepPath(studyId, s.key)} className={cls} aria-current={i === current ? 'step' : undefined}>
            {body}
          </NavLink>
        ) : (
          <div key={s.key} className={cls} title="Start the study in Setup first">{body}</div>
        )
      })}
      <div className="foot">Data: CCRS (CHP)<br />Map © OpenStreetMap contributors</div>
    </nav>
  )
}
