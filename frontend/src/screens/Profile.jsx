import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import ProfileMap from '../components/ProfileMap'
import ReviewList from '../components/ReviewList'
import StripDiagram from '../components/StripDiagram'
import { locationPoints } from '../lib/mapcats'
import { ApiError, api, errorText } from '../lib/api'
import { shortName } from '../lib/strip'
import { vruHeadline } from '../lib/vru'
import { cell, fmt, table, titleCase } from '../lib/tables'
import '../styles/profile.css'

const PROV_LABEL = { gps: 'GPS from the report', gps_dms_corrected: 'GPS from the report, converted from degrees-minutes-seconds',
  fars: 'FARS (NHTSA) point, checked against the report\'s streets', exact: 'Matched by street names', fuzzy: 'Fuzzy name match',
  user: 'Placed by you', unmatched: 'Not placed yet (no coordinates)' }
const provLabel = (k) => PROV_LABEL[k] || (k.startsWith('jev') ? `Jev suggestion ${k.slice(3)}` : k)

function Src({ tid, n }) {
  return <span className="src" tabIndex={0} role="note" aria-label={`Source: table ${tid}`}
    title={`Table ${tid} · computed from ${fmt(n)} CCRS crash records`}>ⓘ</span>
}

function Kpis({ p }) {
  const n = cell(p, 'T1/crashes/value')
  const items = [
    ['Crashes', cell(p, p.kpis.crashes), `${cell(p, 'T1/years/value')} yr`],
    ['KSI', cell(p, p.kpis.ksi_crashes), 'fatal + serious'],
    ['Injury crashes', cell(p, p.kpis.injury_crashes), null],
    ['Per mile · year', cell(p, p.kpis.crashes_per_mi_yr), null],
  ]
  return (
    <div className="sf-kpis" aria-label="Key numbers">
      {items.map(([label, value, sub]) => (
        <div className="sf-kpi" key={label}>
          <div className="sf-kpi__label">{label} <Src tid="T1" n={n} /></div>
          <div className="sf-kpi__value">{fmt(value)}{sub ? <small>{sub}</small> : null}</div>
        </div>
      ))}
    </div>
  )
}

function Bars({ t }) {
  const max = Math.max(1, ...t.rows.map((r) => r.values.crashes))
  return (
    <div className="bars">
      {t.rows.map((r) => (
        <div className="bar" key={r.key}>
          <span className="lab">{r.label}</span>
          <span className="tr" aria-hidden="true">
            {/* the one severity ramp, stacked (#119): orange means serious here as everywhere else */}
            {SEV_PARTS.map(([k]) => (r.values[`sev_${k}`] ? <i key={k} className={`sev-${k}`} style={{ width: `${(100 * r.values[`sev_${k}`]) / max}%` }} /> : null))}
          </span>
          <span className="v mono">{fmt(r.values.crashes)}</span>
        </div>
      ))}
    </div>
  )
}

function Heat({ t }) {
  const hours = [...Array(24).keys()]
  const max = Math.max(1, ...t.rows.flatMap((r) => hours.map((h) => r.values[String(h)])))
  return (
    <div className="heat" role="table" aria-label="Crashes by hour and day">
      <span />
      {hours.map((h) => <span key={h} className="hh">{h % 6 === 0 ? h : ''}</span>)}
      {t.rows.map((r) => (
        <div className="hrow" role="row" key={r.key} style={{ display: 'contents' }}>
          <span className="lab" role="rowheader">{r.label.slice(0, 3)}</span>
          {hours.map((h) => {
            const v = r.values[String(h)]
            return <span key={h} role="cell" className="c" title={`${r.label} ${String(h).padStart(2, '0')}:00 · ${v}`}
              aria-label={`${r.label} ${h}:00, ${v}`}
              style={v ? { background: `color-mix(in srgb, var(--info) ${20 + (80 * v) / max}%, var(--surface-2))` } : undefined} />
          })}
        </div>
      ))}
    </div>
  )
}

// Rate against its critical rate: bar = rate, tick = critical rate, red when over. Scaled per kind (units differ).
function RateBar({ v, max }) {
  const crit = v.critical_rate
  const over = v.over_critical === 'Yes'
  const pct = (x) => `${Math.min(100, (100 * x) / max)}%`
  return (
      <div className="ratecell" title={`${fmt(v.rate)} ${v.rate_unit || ''}${crit != null ? ` · critical ${fmt(crit)} (95%)` : ''}`}>
        <span className={`mono${over ? ' over' : ''}`}>{fmt(v.rate)}</span>
        {crit != null ? (
          <span className="rbar" aria-label={over ? 'over its critical rate' : 'under its critical rate'}>
            <i className={over ? 'over' : ''} style={{ width: pct(v.rate) }} />
            <b style={{ left: pct(crit) }} />
          </span>
        ) : null}
      </div>
  )
}

function RateCell({ v, max }) {
  if (v.rate == null) return <td className="sf-num">—</td>
  return <td><RateBar v={v} max={max} /></td>
}

function Locations({ t, onOpen }) {
  const hasRate = t.rows.some((r) => r.values.rate != null)
  const hasCrit = t.rows.some((r) => r.values.critical_rate != null)
  const maxBy = {}
  for (const r of t.rows) {
    const k = r.values.kind
    maxBy[k] = Math.max(maxBy[k] || 0, r.values.rate || 0, r.values.critical_rate || 0)
  }
  return (
    <div className="sf-table-wrap">
      <table className="sf-table">
        <thead>
          <tr><th>Location</th><th className="sf-num">Crashes</th><th className="sf-num">KSI</th>
            <th className="sf-num">Injury</th><th className="sf-num">Dark</th><th className="sf-num">Per yr</th>
            {hasRate ? <th className={hasCrit ? '' : 'sf-num'}>{hasCrit ? 'Rate vs critical' : 'Rate'}</th> : null}</tr>
        </thead>
        <tbody>
          {t.rows.map((r) => (
            <tr key={r.key} className={r.values.kind === 'segment' ? 'segrow' : ''}>
              <td><button type="button" className="rowlink" onClick={() => onOpen(r)}>{r.label}</button>
                {r.values.kind === 'segment' ? <span className="muted mono kind"> · {fmt(r.values.length_mi, 2)} mi</span> : null}</td>
              <td className="sf-num">{fmt(r.values.crashes)}</td>
              <td className="sf-num">{fmt(r.values.ksi_crashes)}</td>
              <td className="sf-num">{fmt(r.values.injury_crashes)}</td>
              <td className="sf-num">{fmt(r.values.dark_crashes)}</td>
              <td className="sf-num">{fmt(r.values.crashes_per_year)}</td>
              {hasRate ? (hasCrit ? <RateCell v={r.values} max={maxBy[r.values.kind] || 1} />
                : <td className="sf-num" title={r.values.rate_unit || ''}>{fmt(r.values.rate)}</td>) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// B. Which locations need attention first? (#103) Rows, order and numbers straight from T2; the frontend only sorts.
const SEV_PARTS = [['k', 'Fatal'], ['a', 'Serious injury'], ['b', 'Minor injury'], ['c', 'Possible injury'],
  ['u', 'Injury, level not stated'], ['o', 'Property damage']]
const SORTS = [['crashes', 'Crashes', (v) => v.crashes], ['ksi', 'KSI', (v) => v.ksi_crashes],
  ['vru', 'Pedestrians + bicyclists', (v) => v.vru_crashes ?? 0], ['rate', 'Rate vs critical', (v) => v.rate_to_critical ?? -1]]

function SevBar({ v, max }) {
  return (
    <span className="sevbar" aria-hidden="true">
      {SEV_PARTS.map(([k]) => (v[`sev_${k}`] ? <i key={k} className={`sev-${k}`} style={{ width: `${(100 * v[`sev_${k}`]) / max}%` }} /> : null))}
    </span>
  )
}

function Ranking({ p, onOpen }) {
  const t = table(p, 'T2')
  const hasCrit = t.rows.some((r) => r.values.rate_to_critical != null)
  const [sort, setSort] = useState('crashes')
  const [all, setAll] = useState(false)
  const key = SORTS.find(([k]) => k === sort)[2]
  const rows = [...t.rows].filter((r) => r.values.crashes > 0)
    .sort((a, b) => key(b.values) - key(a.values) || b.values.crashes - a.values.crashes || a.label.localeCompare(b.label))
  const shown = all ? rows : rows.slice(0, 5)
  const max = Math.max(1, ...t.rows.map((r) => r.values.crashes))
  const maxBy = {}
  for (const r of t.rows) maxBy[r.values.kind] = Math.max(maxBy[r.values.kind] || 0, r.values.rate || 0, r.values.critical_rate || 0)
  return (
    <section aria-label="Location ranking">
      <div className="sect-h"><h2 className="h3">Which locations need attention first?</h2><Src tid="T2" n={cell(p, 'T1/crashes/value')} /></div>
      <div className="seg strip-dim" role="radiogroup" aria-label="Rank by">
        {SORTS.filter(([k]) => k !== 'rate' || hasCrit).map(([k, label]) => (
          <button key={k} type="button" role="radio" aria-checked={sort === k} className={sort === k ? 'on' : ''} onClick={() => setSort(k)}>{label}</button>
        ))}
      </div>
      <ol className="rank">
        {shown.map((r) => (
          <li key={r.key}>
            <button type="button" className="rowlink" onClick={() => onOpen(r)}>{r.label}</button>
            <span className="mono n" title="Crashes">{fmt(r.values.crashes)}</span>
            <span className="mono n ksi" title="KSI crashes (fatal + serious)">{fmt(r.values.ksi_crashes)} KSI</span>
            <span className={`mono vrun${r.values.vru_crashes ? '' : ' zero'}`} data-testid="rank-vru"
              title="Crashes with a pedestrian or bicyclist (KSI among them)">◯ {fmt(r.values.vru_crashes || 0)} ped/bike{r.values.vru_ksi_crashes ? ` · ${fmt(r.values.vru_ksi_crashes)} KSI` : ''}</span>
            <SevBar v={r.values} max={max} />
            {hasCrit && r.values.critical_rate != null ? <RateBar v={r.values} max={maxBy[r.values.kind] || 1} /> : null}
          </li>
        ))}
      </ol>
      <div className="rank-foot">
        {rows.length > 5 ? <button type="button" className="linkbtn" onClick={() => setAll(!all)}>{all ? 'Show top 5' : `Show all ${rows.length}`}</button> : null}
        <div className="legend">{SEV_PARTS.filter(([k]) => t.rows.some((r) => r.values[`sev_${k}`])).map(([k, l]) => <span key={k}><i className={`sev-${k}`} />{l}</span>)}</div>
      </div>
      <details className="showtable"><summary>Show table</summary><Locations t={t} onOpen={onOpen} /></details>
    </section>
  )
}

// C. How bad, not just how many? (#103) K/A/B/C/(U)/O bars from T3, direct-labelled; KSI called out from T1.
function Severity({ p }) {
  const t = table(p, 'T3')
  const rows = t.rows.filter((r) => r.key !== 'U' || r.values.crashes)
  const max = Math.max(1, ...rows.map((r) => r.values.crashes))
  return (
    <section aria-label="Severity">
      <div className="sect-h"><h2 className="h3">How bad, not just how many?</h2><Src tid="T3" n={cell(p, 'T1/crashes/value')} /></div>
      <p className="ksi-call"><b className="mono">{fmt(cell(p, 'T1/ksi_crashes/value'))}</b> crashes killed or seriously injured someone (KSI).</p>
      <div className="bars sevsum">
        {rows.map((r) => (
          <div className="bar" key={r.key}>
            <span className="lab" title={r.label}>{r.label}</span>
            <span className="tr" aria-hidden="true"><i className={`sev-${r.key.toLowerCase()}`} style={{ width: `${(100 * r.values.crashes) / max}%` }} /></span>
            <span className="v mono">{fmt(r.values.crashes)} · {fmt(r.values.share_pct)}%</span>
          </div>
        ))}
      </div>
      <details className="showtable"><summary>Show table</summary>
        <div className="sf-table-wrap"><table className="sf-table"><thead><tr><th>Severity</th><th className="sf-num">Crashes</th><th className="sf-num">Share %</th></tr></thead>
          <tbody>{t.rows.map((r) => <tr key={r.key}><td>{r.label}</td><td className="sf-num mono">{fmt(r.values.crashes)}</td><td className="sf-num mono">{fmt(r.values.share_pct)}</td></tr>)}</tbody></table></div>
      </details>
    </section>
  )
}

// H. Can I trust these numbers? (#104) One line: how the crashes were located, plus the review list and the
// exclusions, all from T1; the segments add up to every crash the pull read (T1 conservation).
const RULE_LABEL = { outside_buffer: 'outside the corridor buffer', outside_study_limits: 'beyond the study limits',
  cross_street_not_on_corridor: 'at a cross street off the corridor', freeway: 'on a freeway or ramp',
  grade_separated_crossing: 'on a road over or under the corridor', not_on_corridor_street: 'on another street',
  private_property: 'on private property', user_excluded: 'excluded by you', no_segment: 'not on a study segment',
  not_on_freeway: 'not on the freeway', ramp: 'on a freeway ramp' }
// short labels so the line stays one line at the 400 px column; the T1 row labels (ⓘ, export) carry the full wording
const QUALITY = [['located_gps', 'GPS', 'q-gps', "Located by the officer's GPS"],
  ['located_fars', 'FARS', 'q-fars', 'Fatal crashes placed at their FARS point (NHTSA), checked against the streets the report names'], ['located_exact', 'exact', 'q-exact', 'Placed by exact street-name match'],
  ['located_other', 'other', 'q-other', 'Placed by other matching tiers'], ['user_placed', 'by you', 'q-user', 'Placed by you on the review list'],
  ['unplaced', 'to review', 'q-review', 'Not placed yet: open the review list'], ['excluded', 'nearby, outside the corridor', 'q-ex', 'Nearby crashes outside the corridor: show the rules']]

function Quality({ p, excluded, onReview }) {
  const v = (k) => cell(p, `T1/${k}/value`) || 0
  const [open, setOpen] = useState(false)
  const width = QUALITY.reduce((t, [k]) => t + v(k), 0) || 1   // drawing scale only: the bar spans every crash read
  return (
    <section className="quality" aria-label="Data quality">
      <div className="sect-h"><h2 className="h3">Can I trust these numbers?</h2><Src tid="T1" n={cell(p, 'T1/crashes/value')} /></div>
      <div className="qbar" aria-hidden="true">{QUALITY.map(([k, , c]) => (v(k) ? <i key={k} className={c} style={{ width: `${(100 * v(k)) / width}%` }} /> : null))}</div>
      <p className="qline">
        {QUALITY.map(([k, label, c, full]) => {
          if (!v(k)) return null
          if (k === 'unplaced') return <button key={k} type="button" className="linkbtn" title={full} onClick={onReview}><i className={c} />{fmt(v(k))} {label}</button>
          if (k === 'excluded') return <button key={k} type="button" className="linkbtn" title={full} aria-expanded={open} onClick={() => setOpen(!open)}><i className={c} />{fmt(v(k))} {label}</button>
          const dms = k === 'located_gps' ? v('located_gps_dms') : 0       // GPS converted from degrees-minutes-seconds (#143)
          return <span key={k} title={dms ? `${full}; ${fmt(dms)} converted from degrees-minutes-seconds` : full} data-testid={`q-${k}`}>
            <i className={c} />{fmt(v(k))} {label}{dms ? <small className="muted"> ({fmt(dms)} converted)</small> : null}</span>
        })}
      </p>
      {open ? (
        <ul className="kv qrules" aria-label="Excluded, by rule">
          {Object.entries(excluded).sort((a, b) => b[1] - a[1]).map(([r, n]) => <li key={r}><span>{RULE_LABEL[r] || r}</span><span className="mono">{fmt(n)}</span></li>)}
        </ul>
      ) : null}
    </section>
  )
}

// D. Getting better or worse? (#104) Crashes per year from T11, injury / property damage; COVID years banded,
// years with preliminary CCRS reports marked. Bars up to 5 years, a line beyond. No trend line or forecast.
function Trend({ p }) {
  const rows = table(p, 'T11').rows
  const max = Math.max(1, ...rows.map((r) => r.values.crashes))
  const anyCovid = rows.some((r) => r.values.covid === 'Yes')
  const anyPrelim = rows.some((r) => r.values.preliminary)
  return (
    <section aria-label="Crashes by year">
      <div className="sect-h"><h2 className="h3">Getting better or worse?</h2><Src tid="T11" n={cell(p, 'T1/crashes/value')} /></div>
      {rows.length <= 5 ? (
        <div className="trend">
          {rows.map((r) => (
            <div key={r.key} className={`yr${r.values.covid === 'Yes' ? ' covid' : ''}`} data-testid="trend-year">
              <span className="mono n">{fmt(r.values.crashes)}</span>
              <span className="col" aria-hidden="true">
                {SEV_PARTS.map(([k]) => (r.values[`sev_${k}`] ? <i key={k} className={`sev-${k}`} style={{ height: `${(100 * r.values[`sev_${k}`]) / max}%` }} /> : null))}
              </span>
              <span className="mono y">{r.label}{r.values.preliminary ? <b className="prelim" title={`${fmt(r.values.preliminary)} preliminary reports`}>prelim.</b> : null}</span>
            </div>
          ))}
        </div>
      ) : <TrendLine rows={rows} max={max} />}
      <div className="legend small">{SEV_PARTS.filter(([k]) => rows.some((r) => r.values[`sev_${k}`])).map(([k, l]) => <span key={k}><i className={`sev-${k}`} />{l}</span>)}</div>
      {anyCovid ? <p className="muted small-note">Shaded: 2020–2021, when COVID-19 changed travel and crash patterns.</p> : null}
      {anyPrelim ? <p className="muted small-note">prelim.: CCRS still marks some of that year&apos;s reports preliminary; counts may change.</p> : null}
      <details className="showtable"><summary>Show table</summary>
        <div className="sf-table-wrap"><table className="sf-table"><thead><tr><th>Year</th><th className="sf-num">Crashes</th><th className="sf-num">Injury</th>
          <th className="sf-num">Property damage</th><th className="sf-num">KSI</th><th className="sf-num">Preliminary</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.key}><td>{r.label}{r.values.covid === 'Yes' ? ' (COVID)' : ''}</td><td className="sf-num mono">{fmt(r.values.crashes)}</td>
            <td className="sf-num mono">{fmt(r.values.injury_crashes)}</td><td className="sf-num mono">{fmt(r.values.pdo_crashes)}</td>
            <td className="sf-num mono">{fmt(r.values.ksi_crashes)}</td><td className="sf-num mono">{fmt(r.values.preliminary)}</td></tr>)}</tbody></table></div>
      </details>
    </section>
  )
}

function TrendLine({ rows, max }) {
  const W = 460, H = 140, P = 24
  const x = (i) => P + (i * (W - 2 * P)) / Math.max(1, rows.length - 1)
  const y = (n) => H - P - ((H - 2 * P) * n) / max
  const path = (k) => rows.map((r, i) => `${i ? 'L' : 'M'}${x(i)},${y(r.values[k])}`).join(' ')
  const last = rows[rows.length - 1]
  return (
    <svg className="trendline" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Crashes per year, line">
      {rows.map((r, i) => (r.values.covid === 'Yes' ? <rect key={`c${r.key}`} x={x(i) - 12} y={P / 2} width={24} height={H - P * 1.5} className="covidband" /> : null))}
      <path d={path('crashes')} className="l-all" /><path d={path('injury_crashes')} className="l-inj" />
      {rows.map((r, i) => (
        <g key={r.key} data-testid="trend-year">
          <circle cx={x(i)} cy={y(r.values.crashes)} r={4} className="l-all-dot"><title>{`${r.label}: ${r.values.crashes} crashes, ${r.values.injury_crashes} injury`}</title></circle>
          <text x={x(i)} y={H - 6} textAnchor="middle" className="yl">{r.label}{r.values.preliminary ? '*' : ''}</text>
        </g>
      ))}
      <text x={x(rows.length - 1) - 6} y={y(last.values.crashes) - 8} textAnchor="end" className="dl">all crashes</text>
      <text x={x(rows.length - 1) - 6} y={y(last.values.injury_crashes) - 8} textAnchor="end" className="dl">injury</text>
    </svg>
  )
}

// E. Is there a pattern? (#105) Collision type x location from T13: locations in corridor order, types by count;
// empty rows and columns hidden; a number in every cell, shade = crashes (one hue). Sets up Findings (T12).
const TYPE_SHORT = { broadside: 'Broad.', 'rear end': 'Rear', 'side swipe': 'Swipe', 'hit object': 'Object', 'head-on': 'Head-on',
  'vehicle/pedestrian': 'Ped.', other: 'Other', overturned: 'Roll', not_stated: 'n/s' }
const gridName = (name) => String(name).split(' – ').map(shortName).join(' – ')

function Grid({ p, onOpen }) {
  const wrap = useRef(null)
  const [more, setMore] = useState(false)             // columns still past the right edge: say so (#119)
  useEffect(() => {
    const el = wrap.current
    if (!el) return undefined
    const check = () => setMore(el.scrollWidth - el.clientWidth - el.scrollLeft > 2)
    check()
    el.addEventListener('scroll', check)
    window.addEventListener('resize', check)
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(check) : null
    ro?.observe(el)
    if (el.firstElementChild) ro?.observe(el.firstElementChild)
    return () => { el.removeEventListener('scroll', check); window.removeEventListener('resize', check); ro?.disconnect() }
  }, [p])
  const t = table(p, 'T13')
  const t2 = table(p, 'T2')
  const cols = t.columns.filter((c) => c.key !== 'total' && t.rows.some((r) => r.values[c.key]))
  const rows = t.rows.filter((r) => r.values.total)
  const max = Math.max(1, ...rows.flatMap((r) => cols.map((c) => r.values[c.key] || 0)))
  return (
    <section aria-label="Collision type by location">
      <div className="sect-h"><h2 className="h3">Is there a pattern?</h2><Src tid="T13" n={cell(p, 'T1/crashes/value')} /></div>
      <div className="gridwrap" ref={wrap}>
        <table className="grid13">
          <thead><tr><th>Location</th>{cols.map((c) => <th key={c.key} className="sf-num" scope="col" title={c.label}>{TYPE_SHORT[c.key.toLowerCase()] || c.label}</th>)}</tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <th scope="row"><button type="button" className="rowlink" title={r.label} onClick={() => { const row = t2.rows.find((x) => x.key === r.key); if (row) onOpen(row) }}>{gridName(r.label)}</button></th>
                {cols.map((c) => {
                  const n = r.values[c.key] || 0
                  return <td key={c.key} className="sf-num mono" data-testid="grid-cell"
                    style={n ? { background: `color-mix(in srgb, var(--info) ${Math.round(12 + (60 * n) / max)}%, transparent)` } : undefined}>{n || ''}</td>
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {more ? <p className="gridmore" role="note">More columns → scroll the grid</p> : null}
      <p className="muted small-note">Darker = more crashes of that type at that location. Findings tests which of these stand out.</p>
    </section>
  )
}

// F. Pedestrians and bicyclists first (#136, user decision 2026-10-20): right under the trust strip. Headline and the
// "how dangerous" comparison from T19; the locations with the most of each from T2; pedestrian action (T15) and the
// lighting split (T20). Motorcyclists are shown alongside. Every number is a table cell; this only draws them.
const ROAD_USERS = [['ped', 'Pedestrians', 'ped_crashes'], ['bike', 'Bicyclists', 'bike_crashes'], ['ebike', 'E-bikes', 'ebike_crashes'],
  ['escooter', 'E-scooters', 'escooter_crashes'], ['motorcycle', 'Motorcyclists', 'moto_crashes']]
const DANGER = [['ped', 'Pedestrian crashes'], ['bike', 'Bicycle crashes'], ['ebike', 'E-bike crashes'],
  ['escooter', 'E-scooter crashes'], ['motorcycle', 'Motorcycle crashes'],
  ['other', 'All other crashes']]

function Vru({ p, onMap, mapMode }) {
  const t19 = table(p, 'T19'), t2 = table(p, 'T2'), t15 = table(p, 'T15'), t20 = table(p, 'T20')
  const v = (k) => t19.rows.find((r) => r.key === k)?.values || {}
  const h = vruHeadline(t19)
  const rows = DANGER.map(([k, label]) => ({ k, label, ...v(k) })).filter((r) => r.crashes)
  const n = cell(p, 'T1/crashes/value')
  return (
    <section className="vru-sect" aria-label="Pedestrians and bicyclists">
      <div className="sect-h"><h2 className="h3">Pedestrians and bicyclists</h2><Src tid="T19" n={n} /></div>
      <p className="vru-head" data-testid="vru-headline">{h.lead}{h.pct != null ? <b className="mono">{fmt(h.pct)}%</b> : null}{h.rest}</p>
      {rows.length > 1 ? (
        <>
          <h3 className="h4">How dangerous is it? <span className="muted">share of each group&apos;s crashes that killed or seriously injured someone (bars on a 0–100% scale)</span></h3>
          <div className="danger" data-testid="danger">
            {rows.map((r) => (
              <div className={`dg${r.k === 'other' ? ' ref' : ''}`} key={r.k} data-testid={`danger-${r.k}`}>
                <span className="lab">{r.label}</span>
                <span className="tr" aria-hidden="true"><i style={{ width: `${Math.min(100, r.ksi_pct || 0)}%` }} /></span>
                <span className="v mono">{fmt(r.ksi_pct)}%</span>
                <span className="nn mono muted">{fmt(r.ksi_crashes)} of {fmt(r.crashes)}</span>
              </div>
            ))}
          </div>
        </>
      ) : null}
      <ul className="vru">
        {ROAD_USERS.map(([k, label, col]) => {
          const r = v(k)
          const top = t2.rows.filter((x) => x.values[col]).sort((a, b) => b.values[col] - a.values[col] || a.label.localeCompare(b.label)).slice(0, 3)
          return (
            <li key={k} data-testid={`vru-${k}`}>
              <div className="vru-h"><b>{label}</b><span className="mono n">{fmt(r.crashes || 0)}</span><span className="mono ksi">{fmt(r.ksi_crashes || 0)} KSI</span>
                {r.crashes ? <button type="button" className={`linkbtn${mapMode === k ? ' on' : ''}`} aria-pressed={mapMode === k}
                  onClick={() => onMap(mapMode === k ? null : k)}>{mapMode === k ? 'Showing only these on the map' : 'Show only these on the map'}</button> : null}</div>
              {top.length ? <div className="muted vru-top">Most at {top.map((x) => `${x.label} ${fmt(x.values[col])}`).join(' · ')}</div>
                : <div className="muted vru-top">None in this window.</div>}
            </li>
          )
        })}
      </ul>
      {v('ped').crashes ? (
        <div className="ped-ctx">
          <div>
            <div className="sect-h"><h3 className="h4">What the pedestrian was doing</h3><Src tid="T15" n={n} /></div>
            <Bars t={t15} />
          </div>
          <div>
            <div className="sect-h"><h3 className="h4">Day or night</h3><Src tid="T20" n={n} /></div>
            <Bars t={{ ...t20, rows: t20.rows.filter((r) => r.values.crashes) }} />
          </div>
        </div>
      ) : null}
      <details className="showtable"><summary>Show table</summary>
        <div className="sf-table-wrap"><table className="sf-table"><thead><tr><th>Group</th><th className="sf-num">Crashes</th><th className="sf-num">KSI</th>
          <th className="sf-num">KSI % of group</th><th className="sf-num">Share of crashes %</th><th className="sf-num">Share of KSI %</th></tr></thead>
          <tbody>{t19.rows.map((r) => <tr key={r.key}><td>{r.label}</td><td className="sf-num mono">{fmt(r.values.crashes)}</td>
            <td className="sf-num mono">{fmt(r.values.ksi_crashes)}</td><td className="sf-num mono">{r.values.ksi_pct == null ? '—' : fmt(r.values.ksi_pct)}</td>
            <td className="sf-num mono">{fmt(r.values.share_of_crashes_pct)}</td><td className="sf-num mono">{fmt(r.values.share_of_ksi_pct)}</td></tr>)}</tbody></table></div>
        {[t15, t20].map((t) => (
          <div className="sf-table-wrap" key={t.id}><table className="sf-table"><caption>{t.title}</caption><thead><tr><th></th><th className="sf-num">Crashes</th><th className="sf-num">KSI</th><th className="sf-num">Share %</th></tr></thead>
            <tbody>{t.rows.map((r) => <tr key={r.key}><td>{r.label}</td><td className="sf-num mono">{fmt(r.values.crashes)}</td><td className="sf-num mono">{fmt(r.values.ksi_crashes)}</td><td className="sf-num mono">{fmt(r.values.share_pct)}</td></tr>)}</tbody></table></div>
        ))}
      </details>
    </section>
  )
}

function DataSources({ p, pull, onRefresh, busy }) {
  const prov = Object.entries(p.location_provenance || {}).filter(([, v]) => v)
  const cl = pull?.cleaning || {}
  return (
    <details className="adv sources">
      <summary>Where these crashes come from</summary>
      <div className="srcbody">
        <p className="muted">{p.source}. Pulled {pull?.pulled_at?.slice(0, 10)}.</p>
        <div className="lbl">Crash locations</div>
        <ul>{prov.map(([k, v]) => <li key={k}><span>{provLabel(k)}</span><span className="mono">{fmt(v)}</span></li>)}</ul>
        <div className="lbl">Cleaning</div>
        <ul>
          <li><span>Records read</span><span className="mono">{fmt(cl.rows_read)}</span></li>
          <li><span>Deleted by CHP, dropped</span><span className="mono">{fmt(cl.deleted_dropped)}</span></li>
          <li><span>Older report versions, dropped</span><span className="mono">{fmt(cl.duplicate_versions_dropped)}</span></li>
          <li><span>Preliminary, kept and flagged</span><span className="mono">{fmt(cl.preliminary_kept)}</span></li>
          {cl.no_coords_other_city ? (
            <li title={Object.entries(cl.other_cities || {}).map(([c, n]) => `${c} ${n}`).join(', ')}>
              <span>No GPS, filed in a city the corridor doesn&apos;t enter, left out</span><span className="mono">{fmt(cl.no_coords_other_city)}</span></li>
          ) : null}
        </ul>
        <button type="button" className="sf-btn" onClick={onRefresh} disabled={busy}>Pull fresh data from CCRS</button>
      </div>
    </details>
  )
}

function Drill({ row, data, onClose }) {
  if (!data) return <div className="muted">Loading {row.label}…</div>
  const sev = table(data, `T3@${row.key}`)
  const types = table(data, `T4@${row.key}`)
  const light = table(data, `T6@${row.key}`)
  return (
    <div className="drill">
      <button type="button" className="linkbtn" onClick={onClose}>← All locations</button>
      <h2 className="h2">{row.label}</h2>
      <div className="muted mono">{fmt(row.values.crashes)} crashes · {fmt(row.values.ksi_crashes)} KSI · {fmt(row.values.crashes_per_year)} per year <Src tid="T2" n={row.values.crashes} /></div>
      <section><div className="sect-h"><h3 className="h3">Severity</h3><Src tid={sev.id} n={row.values.crashes} /></div>
        <ul className="kv">{sev.rows.filter((r) => r.values.crashes).map((r) => <li key={r.key}><span>{r.label}</span><span className="mono">{fmt(r.values.crashes)}</span></li>)}</ul></section>
      <section><div className="sect-h"><h3 className="h3">Collision type</h3><Src tid={types.id} n={row.values.crashes} /></div><Bars t={types} /></section>
      <section><div className="sect-h"><h3 className="h3">Lighting</h3><Src tid={light.id} n={row.values.crashes} /></div>
        <ul className="kv">{light.rows.map((r) => <li key={r.key}><span>{r.label}</span><span className="mono">{fmt(r.values.crashes)}</span></li>)}</ul></section>
      <section><h3 className="h3">Crash records</h3>
        <div className="sf-table-wrap"><table className="sf-table"><thead><tr><th>Date</th><th>Type</th><th>Sev.</th><th>Roads</th></tr></thead>
          <tbody>{data.crashes.map((c) => (
            <tr key={c.crash_id}><td className="mono">{c.date}{c.hour != null ? ` ${String(c.hour).padStart(2, '0')}h` : ''}</td>
              <td>{titleCase(c.collision_type)}</td><td className="mono">{c.severity}</td>
              <td className="muted">{c.primary_road} / {c.secondary_road}</td></tr>))}</tbody></table></div>
      </section>
    </div>
  )
}

// Crashes the profile counts (placed at a study location), with their location id.
function placedCrashes(crashes, asg) {
  const at = new Map((asg?.assignments || []).filter((a) => a.kind === 'intersection' || a.kind === 'segment')
    .map((a) => [a.crash_id, a]))
  return crashes.filter((c) => at.has(c.crash_id))
    .map((c) => ({ ...c, location_id: at.get(c.crash_id).location_id, station_ft: at.get(c.crash_id).station_ft }))
}

// A. Where along the corridor crashes bunch up (#102); exact numbers per location behind "Show table" (T2)
function Strip({ p, net, crashes, onOpen }) {
  const t2 = table(p, 'T2')
  const station = new Map([...(net.intersections || []).map((i) => [i.id, i.station_ft]),
    ...(net.segments || []).map((s) => [s.id, (s.from_station_ft + s.to_station_ft) / 2])])
  const off = cell(p, 'T1/unplaced/value'), ex = cell(p, 'T1/excluded/value')
  return (
    <section aria-label="Crashes along the corridor">
      <div className="sect-h"><h2 className="h3">Where along the corridor crashes bunch up</h2><Src tid="T2" n={cell(p, 'T1/crashes/value')} /></div>
      <StripDiagram crashes={crashes} intersections={(net.intersections || []).filter((i) => i.is_study !== false)}
        lengthFt={net.length_ft} onOpen={(id) => { const row = t2.rows.find((r) => r.key === id); if (row) onOpen(row) }} />
      {off || ex ? <p className="muted small-note">Not drawn: {fmt(off)} not placed yet (review list), {fmt(ex)} outside the study area.</p> : null}
      <details className="showtable"><summary>Show table</summary>
        <div className="sf-table-wrap"><table className="sf-table"><thead><tr><th>Location</th><th className="sf-num">From A (ft)</th><th className="sf-num">Crashes</th></tr></thead>
          <tbody>{t2.rows.map((r) => <tr key={r.key}><td>{r.label}</td><td className="sf-num mono">{station.has(r.key) ? fmt(Math.round(station.get(r.key))) : '—'}</td>
            <td className="sf-num mono">{fmt(r.values.crashes)}</td></tr>)}</tbody></table></div>
      </details>
    </section>
  )
}

// Starts the CCRS pull in the background and polls its progress (#54): a 10-year pull is ~40 data.ca.gov calls,
// about a minute, so the screen says which step it is on instead of waiting on one frozen request.
async function pullCrashes(studyId, refresh, onStep, poll = 1000) {
  let r = await api(`/studies/${studyId}/crashes/pull?background=true${refresh ? '&refresh=true' : ''}`, { method: 'POST' })
  while (r && r.job) {
    onStep(r.job)
    await new Promise((res) => setTimeout(res, poll))
    const st = await api(`/studies/${studyId}/crashes/pull/status`)
    if (st.state === 'done') return st.summary
    if (st.state === 'error') throw new ApiError(st.status || 500, st.error)
    r = { job: st }
  }
  return r
}

// Step 3: crash profile dashboard. Every number shown comes from the C6 API response.
export default function Profile() {
  const { studyId } = useParams()
  const navigate = useNavigate()
  const [state, setState] = useState({ phase: 'loading' })
  const [drill, setDrill] = useState(null)       // { row, data }
  const [refreshing, setRefreshing] = useState(false)
  const [review, setReview] = useState(null)      // review list data while it's open (#97)
  const [picking, setPicking] = useState(null)    // { ids, done } while a map point is being picked
  const [mapMode, setMapMode] = useState(null)    // 'ped' | 'bike' | 'motorcycle': only those crashes on the map (#105)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const net = await api(`/studies/${studyId}/network`)
        if (!net.line) { if (alive) setState({ phase: 'nocorridor' }); return }
        if (alive) setState({ phase: 'pulling', line: net.line })
        const pull = await pullCrashes(studyId, false, (job) => alive && setState((s) => ({ ...s, job })))
        const [p, cr, asg] = await Promise.all([api(`/studies/${studyId}/profile`), api(`/studies/${studyId}/crashes`),
          api(`/studies/${studyId}/assignment`)])
        if (alive) setState({ phase: 'ready', line: net.line, net, pull, profile: p, crashes: placedCrashes(cr.crashes, asg), excludedByRule: asg.excluded_by_rule || {} })
      } catch (e) {
        if (alive) setState((s) => ({ ...s, phase: 'error', error: errorText(e) }))
      }
    })()
    return () => { alive = false }
  }, [studyId])

  async function refresh() {
    setRefreshing(true)
    try {
      const pull = await pullCrashes(studyId, true, () => {})
      const [p, cr, asg] = await Promise.all([api(`/studies/${studyId}/profile`), api(`/studies/${studyId}/crashes`),
        api(`/studies/${studyId}/assignment`)])
      setState((s) => ({ ...s, pull, profile: p, crashes: placedCrashes(cr.crashes, asg), excludedByRule: asg.excluded_by_rule || {} }))
      setDrill(null)
    } catch (e) {
      setState((s) => ({ ...s, refreshError: errorText(e) }))
    } finally { setRefreshing(false) }
  }

  async function reload() {
    const [p, cr, asg] = await Promise.all([api(`/studies/${studyId}/profile`), api(`/studies/${studyId}/crashes`),
      api(`/studies/${studyId}/assignment`)])
    setState((s) => ({ ...s, profile: p, crashes: placedCrashes(cr.crashes, asg), excludedByRule: asg.excluded_by_rule || {} }))
  }

  async function openReview() {
    setDrill(null)
    setReview(await api(`/studies/${studyId}/review`))
  }

  async function reviewChanged(next) {           // a decision or an undo: the server recounts, the screen follows
    setReview(next)
    setPicking(null)
    await reload()
  }

  async function openLocation(row) {
    setDrill({ row, data: null })
    const data = await api(`/studies/${studyId}/profile/locations/${encodeURIComponent(row.key)}`)
    setDrill({ row, data })
  }

  const locs = useMemo(() => locationPoints(state.net), [state.net])
  const highlight = useMemo(() => (drill?.data ? new Set(drill.data.crashes.map((c) => c.crash_id)) : null), [drill])
  const p = state.profile

  return (
    <section className="profile" aria-label="Crash profile">
      <div className="mapcol">
        <ProfileMap line={state.line} crashes={mapMode ? (state.crashes || []).filter((c) => c[mapMode]) : state.crashes || []} locations={locs} highlight={highlight} selected={drill?.row.key}
          onPick={picking ? (pt) => picking.done(pt) : undefined} />
      </div>
      <div className="datacol">
        {state.phase === 'nocorridor' && (
          <div className="empty"><p>Draw the corridor first. The profile needs the study area.</p>
            <button type="button" className="sf-btn sf-btn--go" onClick={() => navigate(`/s/${studyId}/corridor`)}>Draw the corridor →</button></div>
        )}
        {(state.phase === 'loading' || state.phase === 'pulling') && (
          <div className="empty" role="status"><span className="sf-sig sf-sig--anim"><i /><i /><i /></span>
            <p>{state.phase === 'pulling' ? 'Pulling crashes from CCRS (data.ca.gov). The first pull for a corridor can take a minute.' : 'Loading…'}</p>
            {state.phase === 'pulling' && state.job?.step && state.job.step !== 'Starting' ? (
              <p className="muted mono">{state.job.step}{state.job.total ? ` · ${state.job.done + 1} of ${state.job.total}` : ''}</p>
            ) : null}</div>
        )}
        {state.phase === 'error' && <div className="err" role="alert">{state.error}</div>}
        {state.phase === 'ready' && p && (review ? (
          <ReviewList studyId={studyId} review={review} onChanged={reviewChanged} picking={picking} setPicking={setPicking}
            onClose={() => { setReview(null); setPicking(null) }} />
        ) : drill ? (
          <Drill row={drill.row} data={drill.data} onClose={() => setDrill(null)} />
        ) : (
          <>
            <Kpis p={p} />
            <Quality p={p} excluded={state.excludedByRule || {}} onReview={openReview} />
            <Vru p={p} onMap={setMapMode} mapMode={mapMode} />
            <Strip p={p} net={state.net} crashes={state.crashes || []} onOpen={openLocation} />
            <Ranking p={p} onOpen={openLocation} />
            <Severity p={p} />
            <Trend p={p} />
            <Grid p={p} onOpen={openLocation} />
            {p.caveats.length > 0 && (
              <ul className="caveats" aria-label="Caveats">
                {p.caveats.map((c) => <li key={c.key} className={c.limitation ? 'warn' : ''}>{c.text}</li>)}
              </ul>
            )}
            <section>
              <div className="sect-h"><h2 className="h3">Collision type</h2><Src tid="T4" n={cell(p, 'T1/crashes/value')} /></div>
              <Bars t={table(p, 'T4')} />
              <div className="legend small">{SEV_PARTS.filter(([k]) => table(p, 'T4').rows.some((r) => r.values[`sev_${k}`])).map(([k, l]) => <span key={k}><i className={`sev-${k}`} />{l}</span>)}</div>
            </section>
            <section>
              <div className="sect-h"><h2 className="h3">When crashes happen</h2><Src tid="T9" n={cell(p, 'T1/crashes/value')} /></div>
              <Heat t={table(p, 'T9')} />
            </section>
            <DataSources p={p} pull={state.pull} onRefresh={refresh} busy={refreshing} />
            {state.refreshError ? <div className="err" role="alert">{state.refreshError}</div> : null}
            <div className="cta-bar"><button type="button" className="sf-btn sf-btn--go" onClick={() => navigate(`/s/${studyId}/findings`)}>See findings →</button></div>
          </>
        ))}
      </div>
    </section>
  )
}
