import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import N10Diagram from '../components/N10Diagram'
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
  gps_sign_corrected: "GPS from the report, the longitude's missing minus sign restored",
  gps_offset_applied: 'GPS from the report, moved by the distance and direction the report states', unique_pair: 'Matched by street names (they meet at only one place)',
  verified_typo: 'Matched after correcting a small typo (one possible street, confirmed by the cross street)',
  freeway_offset: 'Freeway crash placed by the report: from the reference street, ramp terminal or connector, plus the stated distance',
  approximate: 'Approximate (usually within 0.5 mi): a freeway crash with no usable GPS, placed by the report',
  postmile: 'At the Caltrans postmile of the mile marker the report gives, on the state route',
  fars: 'FARS (NHTSA) point, checked against the report\'s streets', exact: 'Matched by street names', fuzzy: 'Fuzzy name match',
  user: 'Placed by you', unmatched: 'Not placed yet (no coordinates)' }
const provLabel = (k) => PROV_LABEL[k] || (k.startsWith('jev') ? `Jev suggestion ${k.slice(3)}` : k)

// ⓘ citation; a table built from a CCRS table missing a year in this pull carries its note, and the mark turns red (#188)
function Src({ tid, n, p }) {
  const note = p?.tables?.find((t) => t.id === tid)?.note
  return <span className={`src${note ? ' src-note' : ''}`} tabIndex={0} role="note" aria-label={`Source: table ${tid}${note ? `. ${note}` : ''}`}
    title={`Table ${tid} · computed from ${fmt(n)} CCRS crash records${note ? `\n${note}` : ''}`}>ⓘ</span>
}

function Kpis({ p }) {
  const n = cell(p, 'T1/crashes/value')
  // #269: Crashes, KSI, Fatal as its own number when there is one, per mile·year
  const fatal = cell(p, 'T1/fatal_crashes/value')
  const items = [
    ['Crashes', cell(p, p.kpis.crashes), `${cell(p, 'T1/years/value')} yr`],
    ['KSI', cell(p, p.kpis.ksi_crashes), 'fatal + serious'],
    ...(fatal ? [['Fatal', fatal, null]] : []),
    ['Per mile · year', cell(p, p.kpis.crashes_per_mi_yr), null],
  ]
  return (
    <div className={`sf-kpis n${items.length}`} aria-label="Key numbers">
      {items.map(([label, value, sub]) => (
        <div className="sf-kpi" key={label}>
          <div className="sf-kpi__label">{label} <Src tid="T1" n={n} p={p} /></div>
          <div className="sf-kpi__value">{fmt(value)}{sub ? <> <small>{sub}</small></> : null}</div>
        </div>
      ))}
    </div>
  )
}

function Bars({ t, testid }) {
  const max = Math.max(1, ...t.rows.map((r) => r.values.crashes))
  return (
    <div className="bars">
      {t.rows.map((r) => (
        <div className="bar" key={r.key} data-testid={testid}>
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

// #265: the standard safety-section tables (#52), drawn straight from their cells; only bar widths are computed here.
const hasRows = (t) => Boolean(t?.rows?.some((r) => r.values.crashes))
const sevLegend = (t) => (
  <div className="legend small">{SEV_PARTS.filter(([k]) => t.rows.some((r) => r.values[`sev_${k}`])).map(([k, l]) => <span key={k}><i className={`sev-${k}`} />{l}</span>)}</div>
)

function CountTable({ t }) {
  return (
    <details className="showtable"><summary>Show table</summary>
      <div className="sf-table-wrap"><table className="sf-table">
        <thead><tr><th>{t.title}</th><th className="sf-num">Crashes</th><th className="sf-num">KSI</th><th className="sf-num">Share %</th><MarkTh t={t} /></tr></thead>
        <tbody>{t.rows.map((r) => (
          <tr key={r.key}><th scope="row">{r.label.trim()}</th>
            {['crashes', 'ksi_crashes', 'share_pct'].map((k) => <td key={k} className="sf-num mono">{fmt(r.values[k])}</td>)}<MarkTd t={t} r={r} /></tr>))}</tbody>
      </table></div>
    </details>
  )
}

// small numbers (user decision 2026-10-25, docs/03): a group of fewer than min_share_n crashes shows counts only
// ("1 of 6") with a "too few to compare" note, never a percentage or a bar
// the threshold comes from the server (profile.MIN_SHARE_N, #271)
const minN = (p) => p?.min_share_n ?? 0
const TooFew = ({ n, min }) => <p className="muted small-note">Too few to compare ({fmt(n)} crashes; shares need {fmt(min)} or more).</p>
// the "n < 10" mark the server puts on rows whose share is of too few crashes; tables show every value (#271)
const hasMark = (t) => t.rows.some((r) => r.values.small_base)
const MarkTh = ({ t }) => (hasMark(t) ? <th>Base</th> : null)
const MarkTd = ({ t, r }) => (hasMark(t) ? <td className="muted mono small">{r.values.small_base || ''}</td> : null)
// counts only, "1 of 6", for a group too small for shares or bars
function CountList({ rows, n, min, testid }) {
  return (
    <>
      <ul className="kv counts" data-testid={testid}>{rows.map((r) => <li key={r.key}><span>{r.label.trim()}</span>
        <span className="mono">{fmt(r.values.crashes)} of {fmt(n)}</span></li>)}</ul>
      <TooFew n={n} min={min} />
    </>
  )
}

// hit and run, DUI and speed (T14): one compact row each; "of which" rows indented; zero rows hidden in a drill-in
function Flags({ t, p, n, label, hideZero }) {
  if (!hasRows(t)) return null
  const small = n < minN(p)
  const rows = hideZero ? t.rows.filter((r) => r.values.crashes) : t.rows
  const max = Math.max(1, ...rows.map((r) => r.values.crashes))
  return (
    <div className="flags" aria-label={label} role="group">
      <div className="sect-h"><h3 className="h3">Hit and run, DUI and speed</h3><Src tid={t.id} n={n} p={p} /></div>
      <div className="bars">
        {rows.map((r) => (
          <div className={`bar${r.label.startsWith(' ') ? ' sub' : ''}${small ? ' nobar' : ''}`} key={r.key} data-testid="flag-row">
            <span className="lab">{r.label.trim()}</span>
            {small ? null : <span className="tr" aria-hidden="true"><i style={{ width: `${(100 * r.values.crashes) / max}%` }} /></span>}
            <span className="v mono">{small ? `${fmt(r.values.crashes)} of ${fmt(n)}` : fmt(r.values.crashes)}</span>
            <span className="muted mono small">{fmt(r.values.ksi_crashes)} KSI{small ? '' : ` · ${fmt(r.values.share_pct)}%`}</span>
          </div>
        ))}
      </div>
      {small ? <TooFew n={n} min={minN(p)} /> : null}
    </div>
  )
}

// E2. Why did they crash? (#265): the primary collision factor in the 24 SWITRS categories (T18), then T14
function Why({ p, suffix = '', n, label = 'Why did they crash?', h = 'h2' }) {
  const pcf = p.tables.find((x) => x.id === `T18${suffix}`)
  const flags = p.tables.find((x) => x.id === `T14${suffix}`)
  if (!hasRows(pcf) && !hasRows(flags)) return null
  const H = h
  return (
    <section aria-label={label}>
      {hasRows(pcf) ? (<>
        <div className="sect-h"><H className="h3">Why did they crash?</H><Src tid={pcf.id} n={n} p={p} /></div>
        <p className="muted small-note">Primary collision factor, in the 24 SWITRS categories.</p>
        <Bars t={pcf} testid="pcf-bar" />
        {sevLegend(pcf)}
        <CountTable t={pcf} />
      </>) : null}
      <Flags t={flags} p={p} n={n} hideZero={Boolean(suffix)}
        label={suffix ? 'Hit and run, DUI and speed (this location)' : 'Hit and run, DUI and speed'} />
    </section>
  )
}

// broadside split (T17), under Collision type: shares of broadside, as T17 states them
function Broadside({ p, n }) {
  const t = p.tables.find((x) => x.id === 'T17')
  if (!hasRows(t)) return null
  const base = t.rows.reduce((a, r) => a + r.values.crashes, 0)           // the broadside crashes the shares are of
  return (
    <div className="broadside small" role="group" aria-label="Broadside: left turn vs right angle">
      Broadside crashes: {t.rows.map((r, i) => (
        <span key={r.key}>{i ? ' · ' : ''}{r.label.split(' (')[0].toLowerCase()} <b className="mono">{fmt(r.values.crashes)}</b>
          {base < minN(p) ? ` of ${fmt(base)}` : ` (${fmt(r.values.share_pct)}%)`}</span>
      ))} <Src tid="T17" n={n} p={p} />
      {base < minN(p) ? <TooFew n={base} min={minN(p)} /> : null}
    </div>
  )
}

// Conditions (#265): movement of the party at fault, weather, road surface, lighting; folded by default
const CONDITIONS = [['T16', 'Movement before the collision (party at fault)'], ['T7', 'Weather'], ['T8', 'Road surface'], ['T6', 'Lighting']]
function Conditions({ p, n }) {
  const blocks = CONDITIONS.map(([id, name]) => [p.tables.find((x) => x.id === id), name]).filter(([t]) => hasRows(t))
  if (!blocks.length) return null
  return (
    <details className="adv conditions">
      <summary>Conditions</summary>
      {blocks.map(([t, name]) => (
        <section key={t.id} aria-label={name}>
          <div className="sect-h"><h3 className="h3">{name}</h3><Src tid={t.id} n={n} p={p} /></div>
          <Bars t={{ ...t, rows: t.rows.map((r) => ({ ...r, label: r.label.trim() })) }} />
          <CountTable t={t} />
        </section>
      ))}
    </details>
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

// When crashes happen (#269): hour of day (24 bars, T26) and day of week (7 bars, T27), severity-stacked; every bar
// is a table cell. The 7 x 24 grid (T9) is folded behind "Show hour × day grid".
function ColBars({ t, label, short }) {
  const max = Math.max(1, ...t.rows.map((r) => r.values.crashes))
  return (
    <div className="colbars" role="group" aria-label={label}>
      {t.rows.map((r) => (
        <div className="cb" key={r.key} data-testid="colbar" title={`${r.label}: ${fmt(r.values.crashes)}`}
          aria-label={`${r.label}, ${r.values.crashes}`}>
          <span className="tr" aria-hidden="true">
            {SEV_PARTS.map(([k]) => (r.values[`sev_${k}`] ? <i key={k} className={`sev-${k}`} style={{ height: `${(100 * r.values[`sev_${k}`]) / max}%` }} /> : null))}
          </span>
          <span className="lab">{short(r)}</span>
        </div>
      ))}
    </div>
  )
}

function When({ p }) {
  const n = cell(p, 'T1/crashes/value')
  const hours = table(p, 'T26')
  const days = table(p, 'T27')
  return (
    <section aria-label="When crashes happen">
      <div className="sect-h"><h2 className="h3">When crashes happen</h2><Src tid="T26" n={n} p={p} /></div>
      {hours?.rows?.length ? <ColBars t={hours} label="Crashes by hour of day"
        short={(r) => (r.key === 'not_stated' ? 'n/s' : Number(r.key) % 6 === 0 ? r.label : '')} /> : null}
      {days?.rows?.length ? <><div className="sect-h"><h3 className="h3">Day of week</h3><Src tid="T27" n={n} p={p} /></div>
        <ColBars t={days} label="Crashes by day of week" short={(r) => (r.key === 'not_stated' ? 'n/s' : r.label.slice(0, 3))} /></> : null}
      {hours?.rows?.length ? sevLegend(hours) : null}
      <details className="showtable"><summary>Show hour × day grid</summary>
        <div className="sect-h"><span /><Src tid="T9" n={n} p={p} /></div><Heat t={table(p, 'T9')} /></details>
    </section>
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
      <div className="sect-h"><h2 className="h3">Which locations need attention first?</h2><Src tid="T2" n={cell(p, 'T1/crashes/value')} p={p} /></div>
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
// State-highway crash rates (#287, user decision 2026-10-26): Caltrans Traffic Census AADT on each study segment of a
// state-route corridor (T22) and the corridor's rate year by year (T23). Every number is a cell; a row above the
// corridor average is marked. A rate on fewer than 10 crashes shows its count only (docs/03 small numbers, #296).
// Trucks (T24): heavy-truck-involved crashes per million 3+ axle truck-miles, folded under "Trucks".
// Segment crashes only until #297 (user); Caltrans' statewide averages wait for #294.
const SHS_DETAIL = [['crashes', 'Crashes'], ['fi_crashes', 'Fatal + injury'], ['fatal_crashes', 'Fatal'], ['length_mi', 'Length (mi)'],
  ['aadt', 'AADT'], ['mvm', 'MVM'], ['rate_all', 'All / MVM'], ['rate_fi', 'Fatal + injury / MVM'], ['rate_fatal', 'Fatal / MVM'],
  ['corridor_rate_all', 'Corridor average'], ['ratio_to_corridor', '÷ average']]
function ShsRates({ p }) {
  const t = p.tables.find((x) => x.id === 'T22')
  const by = p.tables.find((x) => x.id === 'T23')
  const tk = p.tables.find((x) => x.id === 'T24')
  if (!t?.rows?.length) return null
  const n = t.rows.reduce((a, r) => a + r.values.crashes, 0)
  const sources = [...new Set(t.rows.map((r) => r.values.source))]
  const years = [...new Set(t.rows.map((r) => r.values.count_years))]
  const sc = t.scope || {}
  const rate = (r, k) => (r.values.small_base ? '–' : fmt(r.values[k]))
  return (
    <section aria-label="State-highway crash rates">
      <div className="sect-h"><h2 className="h3">State-highway crash rates</h2><Src tid="T22" n={n} p={p} /></div>
      <p className="muted small-note">Crashes per million vehicle-miles (MVM). AADT: {sources.join('; ')}, count years {years.join('; ')}.{' '}
        {sc.small ? `Corridor average: too few crashes to compare (${fmt(sc.rated_crashes)}).`
          : `Corridor average ${fmt(sc.corridor_rate_all ?? t.rows[0].values.corridor_rate_all)} crashes per MVM.`}{' '}
        Caltrans&apos; statewide averages are not shown yet.</p>
      {sc.text ? <p className="muted small-note" data-testid="shs-scope">{sc.text}</p> : null}
      <div className="sf-table-wrap"><table className="sf-table shs" data-testid="shs-rates">
        <thead><tr><th>Segment</th><th className="sf-num">Crashes</th><th className="sf-num">AADT</th><th className="sf-num">Length (mi)</th>
          <th className="sf-num">All / MVM</th><th className="sf-num">Fatal + injury / MVM</th><th className="sf-num">÷ average</th></tr></thead>
        <tbody>{t.rows.map((r) => {
          const v = r.values
          return (
            <tr key={r.key} className={!v.small_base && v.ratio_to_corridor > 1 ? 'over' : ''}
              title={`AADT ${fmt(v.aadt)} (window average) · ${fmt(v.mvm)} MVM · count years ${v.count_years} · ${v.source}`}>
              <th scope="row">{titleCase(r.label)}</th>
              {['crashes', 'aadt', 'length_mi'].map((k) => <td key={k} className="sf-num mono">{fmt(v[k])}</td>)}
              <td className="sf-num mono">{rate(r, 'rate_all')}</td><td className="sf-num mono">{rate(r, 'rate_fi')}</td>
              {v.small_base ? <td className="sf-num muted small">too few to compare</td>
                : <td className="sf-num mono">{fmt(v.ratio_to_corridor)}</td>}
            </tr>
          )
        })}</tbody>
      </table></div>
      <details className="showtable"><summary>Show table</summary>
        <div className="sf-table-wrap"><table className="sf-table" data-testid="shs-detail">
          <thead><tr><th>Segment</th>{SHS_DETAIL.map(([k, l]) => <th key={k} className="sf-num">{l}</th>)}<MarkTh t={t} /></tr></thead>
          <tbody>{t.rows.map((r) => <tr key={r.key}><th scope="row">{titleCase(r.label)}</th>
            {SHS_DETAIL.map(([k]) => <td key={k} className="sf-num mono">{fmt(r.values[k])}</td>)}<MarkTd t={t} r={r} /></tr>)}</tbody>
        </table></div>
      </details>
      {tk?.rows?.length ? (
        <details className="showtable"><summary>Trucks (3+ axles)</summary>
          <p className="muted small-note" data-testid="shs-trucks-scope">{tk.scope?.text} Truck AADT count years{' '}
            {[...new Set(tk.rows.map((r) => r.values.count_years))].join('; ')}.{' '}
            {tk.scope?.small ? `Corridor truck average: too few crashes to compare (${fmt(tk.scope.rated_crashes)}).`
              : `Corridor truck average ${fmt(tk.scope?.corridor_rate_truck)} per million truck-miles.`}</p>
          <div className="sf-table-wrap"><table className="sf-table shs" data-testid="shs-trucks">
            <thead><tr><th>Segment</th><th className="sf-num">Truck crashes</th><th className="sf-num">3+ axle AADT</th>
              <th className="sf-num">Per million truck-miles</th><th className="sf-num">÷ average</th></tr></thead>
            <tbody>{tk.rows.map((r) => {
              const v = r.values
              return (
                <tr key={r.key} className={!v.small_base && v.ratio_to_corridor > 1 ? 'over' : ''}
                  title={`${fmt(v.truck_mvm)} million truck-miles · ${fmt(v.length_mi)} mi · count years ${v.count_years} · ${v.source}`}>
                  <th scope="row">{titleCase(r.label)}</th>
                  <td className="sf-num mono">{fmt(v.truck_crashes)}</td><td className="sf-num mono">{fmt(v.trucks_3plus)}</td>
                  <td className="sf-num mono">{rate(r, 'rate_truck')}</td>
                  {v.small_base ? <td className="sf-num muted small">too few to compare</td>
                    : <td className="sf-num mono">{fmt(v.ratio_to_corridor)}</td>}
                </tr>
              )
            })}</tbody>
          </table></div>
          <Src tid="T24" n={tk.scope?.rated_crashes} p={p} />
        </details>
      ) : null}
      {by?.rows?.length ? (
        <details className="showtable"><summary>By year</summary>
          <div className="sf-table-wrap"><table className="sf-table" data-testid="shs-by-year">
            <thead><tr><th>Year</th><th className="sf-num">Crashes</th><th className="sf-num">MVM</th><th className="sf-num">All / MVM</th><th className="sf-num">Fatal + injury / MVM</th></tr></thead>
            <tbody>{by.rows.map((r) => <tr key={r.key}><td className="mono">{r.label}</td>
              {['crashes', 'mvm'].map((k) => <td key={k} className="sf-num mono">{fmt(r.values[k])}</td>)}
              {['rate_all', 'rate_fi'].map((k) => <td key={k} className="sf-num mono">{rate(r, k)}</td>)}</tr>)}</tbody>
          </table></div>
          {by.rows.some((r) => r.values.small_base) ? <p className="muted small-note">– a year with fewer than {minN(p)} crashes: too few to compare.</p> : null}
          <Src tid="T23" n={n} p={p} />
        </details>
      ) : null}
    </section>
  )
}

// Ramps (#287; user decision 2026-10-30, docs/03, #300): crashes per million vehicles on each Caltrans ramp a crash
// is identified on (T25), with the latest count at or before each year; the scope line counts every ramp crash.
const rampName = (s) => titleCase(s).replace(/\b([NSEW])b\b/g, '$1B').replace(/\b(On|Off|To|From|Fr)\b/g, (m) => m.toLowerCase())
function ShsRamps({ p }) {
  const t = p.tables.find((x) => x.id === 'T25')
  if (!t) return null
  const n = t.rows.reduce((a, r) => a + r.values.crashes, 0)
  const rate = (r) => (r.values.small_base ? '–' : fmt(r.values.rate_all))
  return (
    <section aria-label="Ramp crash rates">
      <div className="sect-h"><h2 className="h3">Ramp crash rates</h2><Src tid="T25" n={n} p={p} /></div>
      <p className="muted small-note">Crashes per million vehicles (MV) on each Caltrans ramp, from the district ramp ADT: the
        latest count at or before each year. {t.scope?.text}</p>
      {t.rows.length ? (
        <>
          <div className="sf-table-wrap"><table className="sf-table shs" data-testid="shs-ramps">
            <thead><tr><th>Ramp</th><th className="sf-num">Crashes</th><th className="sf-num">Ramp ADT</th>
              <th className="sf-num">Per MV</th><th>Count years</th></tr></thead>
            <tbody>{t.rows.map((r) => {
              const v = r.values
              return (
                <tr key={r.key} title={`${fmt(v.mv)} MV · ${v.source}${v.picked ? ` · ${fmt(v.picked)} picked by the engineer` : ''}`}>
                  <th scope="row">{rampName(r.label)}<br /><span className="muted small mono">{v.postmile}</span></th>
                  <td className="sf-num mono">{fmt(v.crashes)}</td><td className="sf-num mono">{fmt(v.adt)}</td>
                  <td className="sf-num mono">{rate(r)}</td><td className="muted small">{v.count_years}</td>
                </tr>
              )
            })}</tbody>
          </table></div>
          {t.rows.some((r) => r.values.small_base) ? <p className="muted small-note">– a ramp with fewer than {minN(p)} crashes: too few to compare.</p> : null}
        </>
      ) : null}
    </section>
  )
}

function Severity({ p }) {
  const t = table(p, 'T3')
  const rows = t.rows.filter((r) => r.key !== 'U' || r.values.crashes)
  const max = Math.max(1, ...rows.map((r) => r.values.crashes))
  const total = t.rows.reduce((a, r) => a + r.values.crashes, 0)
  const small = total < minN(p)
  return (
    <section aria-label="Severity">
      <div className="sect-h"><h2 className="h3">How bad, not just how many?</h2><Src tid="T3" n={cell(p, 'T1/crashes/value')} p={p} /></div>
      <p className="ksi-call"><b className="mono">{fmt(cell(p, 'T1/ksi_crashes/value'))}</b> crashes killed or seriously injured someone (KSI).</p>
      {small ? <CountList rows={rows} n={total} min={minN(p)} /> : (
        <div className="bars sevsum">
          {rows.map((r) => (
            <div className="bar" key={r.key}>
              <span className="lab" title={r.label}>{r.label}</span>
              <span className="tr" aria-hidden="true"><i className={`sev-${r.key.toLowerCase()}`} style={{ width: `${(100 * r.values.crashes) / max}%` }} /></span>
              <span className="v mono">{fmt(r.values.crashes)} · {fmt(r.values.share_pct)}%</span>
            </div>
          ))}
        </div>
      )}
      <details className="showtable"><summary>Show table</summary>
        <div className="sf-table-wrap"><table className="sf-table"><thead><tr><th>Severity</th><th className="sf-num">Crashes</th><th className="sf-num">Share %</th><MarkTh t={t} /></tr></thead>
          <tbody>{t.rows.map((r) => <tr key={r.key}><td>{r.label}</td><td className="sf-num mono">{fmt(r.values.crashes)}</td><td className="sf-num mono">{fmt(r.values.share_pct)}</td><MarkTd t={t} r={r} /></tr>)}</tbody></table></div>
      </details>
    </section>
  )
}

// H. Can I trust these numbers? (#104) One line: how the crashes were located, plus the review list and the
// exclusions, all from T1; the segments add up to every crash the pull read (T1 conservation).
const RULE_LABEL = { outside_buffer: 'outside the corridor buffer', outside_study_limits: 'beyond the study limits',
  fars_off_corridor: 'fatal, FARS places it elsewhere on its roads',
  cross_street_not_on_corridor: 'at a cross street off the corridor', freeway: 'on a freeway or ramp',
  grade_separated_crossing: 'on a road over or under the corridor', not_on_corridor_street: 'on another street',
  private_property: 'on private property', user_excluded: 'excluded by you', no_segment: 'not on a study segment',
  not_on_freeway: 'not on the freeway', ramp: 'on a freeway ramp' }
// short labels so the line stays one line at the 400 px column; the T1 row labels (ⓘ, export) carry the full wording
const QUALITY = [['located_gps', 'GPS', 'q-gps', "Located by the officer's GPS"],
  ['located_fars', 'FARS', 'q-fars', 'Fatal crashes placed at their FARS point (NHTSA), checked against the streets the report names'], ['located_exact', 'exact', 'q-exact', 'Placed by exact street-name match'],
  ['located_unique_pair', 'one possible corner', 'q-pair', "Placed where the report's two streets meet at only one place (a direction or suffix the report leaves out may differ)"],
  ['located_freeway', 'freeway, approximate', 'q-other', 'Freeway crashes with no usable GPS, placed approximately (usually within 0.5 mi) by the report'],
  ['located_other', 'other', 'q-other', 'Placed by other matching tiers'], ['user_placed', 'by you', 'q-user', 'Placed by you on the review list'],
  ['unplaced', 'to review', 'q-review', 'Not placed yet: open the review list'], ['excluded', 'nearby, outside the corridor', 'q-ex', 'Nearby crashes outside the corridor: show the rules']]

function Quality({ p, excluded, onReview }) {
  const v = (k) => cell(p, `T1/${k}/value`) || 0
  const warn = p.caveats.filter((c) => c.limitation)          // #269: data limitations sit in the trust line
  const [open, setOpen] = useState(false)
  const width = QUALITY.reduce((t, [k]) => t + v(k), 0) || 1   // drawing scale only: the bar spans every crash read
  return (
    <section className="quality" aria-label="Data quality">
      <div className="sect-h"><h2 className="h3">Can I trust these numbers?</h2><Src tid="T1" n={cell(p, 'T1/crashes/value')} p={p} /></div>
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
      {warn.length ? (
        <ul className="caveats" aria-label="Data limitations">
          {warn.map((c) => <li key={c.key} className="warn">{c.text}</li>)}
        </ul>
      ) : null}
      {v('fatal_unplaced') ? <p className="qline"><button type="button" className="linkbtn q-fatal" onClick={onReview} data-testid="q-fatal">
        ⚑ {fmt(v('fatal_unplaced'))} fatal crash{v('fatal_unplaced') === 1 ? '' : 'es'} without a location</button></p> : null}
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
      <div className="sect-h"><h2 className="h3">Getting better or worse?</h2><Src tid="T11" n={cell(p, 'T1/crashes/value')} p={p} /></div>
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
    // a column whose right edge is past the grid's visible edge (#266: scrollWidth also counts overflow that isn't a
    // column, and said so on Crenshaw with all 8 columns visible)
    const check = () => {
      const last = el.querySelector('thead th:last-child')
      setMore(Boolean(last) && last.getBoundingClientRect().right - el.getBoundingClientRect().right > 2)
    }
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
  const t4 = table(p, 'T4')                         // the corridor's collision-type totals (#269: no separate bars)
  const total = (k) => t4.rows.find((r) => r.key === k)?.values.crashes
  return (
    <section aria-label="Collision type by location">
      <div className="sect-h"><h2 className="h3">Is there a pattern?</h2><Src tid="T13" n={cell(p, 'T1/crashes/value')} p={p} /></div>
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
          <tfoot><tr data-testid="grid-total"><th scope="row">All crashes <Src tid="T4" n={cell(p, 'T1/crashes/value')} p={p} /></th>
            {cols.map((c) => <td key={c.key} className="sf-num mono" title={c.label}>{fmt(total(c.key))}</td>)}</tr></tfoot>
        </table>
      </div>
      {more ? <p className="gridmore" role="note">More columns → scroll the grid</p> : null}
      <p className="muted small-note">Darker = more crashes of that type at that location. Findings tests which of these stand out.</p>
      <Broadside p={p} n={cell(p, 'T1/crashes/value')} />
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
  const m = minN(p)
  const h = vruHeadline(t19, m)
  const rows = DANGER.map(([k, label]) => ({ k, label, ...v(k) })).filter((r) => r.crashes)
  const n = cell(p, 'T1/crashes/value')
  const peds = v('ped').crashes || 0
  return (
    <section className="vru-sect" aria-label="Pedestrians and bicyclists">
      <div className="sect-h"><h2 className="h3">Pedestrians and bicyclists</h2><Src tid="T19" n={n} p={p} /></div>
      <p className="vru-head" data-testid="vru-headline">{h.lead}{h.pct != null ? <b className="mono">{fmt(h.pct)}%</b> : null}{h.rest}</p>
      {rows.length > 1 ? (
        <>
          <h3 className="h4">How dangerous is it? <span className="muted">share of each group&apos;s crashes that killed or seriously injured someone (bars on a 0–100% scale)</span></h3>
          <div className="danger" data-testid="danger">
            {rows.map((r) => (
              <div className={`dg${r.k === 'other' ? ' ref' : ''}${r.crashes < m ? ' few' : ''}`} key={r.k} data-testid={`danger-${r.k}`}>
                <span className="lab">{r.label}</span>
                {r.crashes < m ? <span className="v mono muted">—</span> : <>
                  <span className="tr" aria-hidden="true"><i style={{ width: `${Math.min(100, r.ksi_pct || 0)}%` }} /></span>
                  <span className="v mono">{fmt(r.ksi_pct)}%</span></>}
                <span className="nn mono muted">{fmt(r.ksi_crashes)} of {fmt(r.crashes)}</span>
              </div>
            ))}
            {rows.some((r) => r.crashes < m) ? <p className="muted small-note">Too few to compare for groups under {fmt(m)} crashes: counts only.</p> : null}
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
      {peds ? (
        <div className="ped-ctx" data-testid="ped-daynight">
          <div>
            <div className="sect-h"><h3 className="h4">What the pedestrian was doing</h3><Src tid="T15" n={n} p={p} /></div>
            {peds < m ? <CountList rows={t15.rows.filter((r) => r.values.crashes)} n={peds} min={m} /> : <Bars t={t15} />}
          </div>
          <div>
            <div className="sect-h"><h3 className="h4">Day or night</h3><Src tid="T20" n={n} p={p} /></div>
            {peds < m ? <CountList rows={t20.rows.filter((r) => r.values.crashes)} n={peds} min={m} />
              : <Bars t={{ ...t20, rows: t20.rows.filter((r) => r.values.crashes) }} />}
          </div>
        </div>
      ) : null}
      <details className="showtable"><summary>Show table</summary>
        <div className="sf-table-wrap"><table className="sf-table"><thead><tr><th>Group</th><th className="sf-num">Crashes</th><th className="sf-num">KSI</th>
          <th className="sf-num">KSI % of group</th><th className="sf-num">Share of crashes %</th><th className="sf-num">Share of KSI %</th><MarkTh t={t19} /></tr></thead>
          <tbody>{t19.rows.map((r) => <tr key={r.key}><td>{r.label}</td><td className="sf-num mono">{fmt(r.values.crashes)}</td>
            <td className="sf-num mono">{fmt(r.values.ksi_crashes)}</td><td className="sf-num mono">{r.values.ksi_pct == null ? '—' : fmt(r.values.ksi_pct)}</td>
            <td className="sf-num mono">{fmt(r.values.share_of_crashes_pct)}</td><td className="sf-num mono">{fmt(r.values.share_of_ksi_pct)}</td><MarkTd t={t19} r={r} /></tr>)}</tbody></table></div>
        {[t15, t20].map((t) => (
          <div className="sf-table-wrap" key={t.id}><table className="sf-table"><caption>{t.title}</caption><thead><tr><th></th><th className="sf-num">Crashes</th><th className="sf-num">KSI</th><th className="sf-num">Share %</th><MarkTh t={t} /></tr></thead>
            <tbody>{t.rows.map((r) => <tr key={r.key}><td>{r.label}</td><td className="sf-num mono">{fmt(r.values.crashes)}</td><td className="sf-num mono">{fmt(r.values.ksi_crashes)}</td><td className="sf-num mono">{fmt(r.values.share_pct)}</td><MarkTd t={t} r={r} /></tr>)}</tbody></table></div>
        ))}
      </details>
    </section>
  )
}

function DataSources({ p, pull, onRefresh, busy }) {
  const prov = Object.entries(p.location_provenance || {}).filter(([, v]) => v)
  const notes = p.caveats.filter((c) => !c.limitation)        // #269: every other caveat, here, never dropped
  const cl = pull?.cleaning || {}
  return (
    <details className="adv sources">
      <summary>Where these crashes come from</summary>
      <div className="srcbody">
        {notes.length ? (
          <ul className="caveats" aria-label="Caveats">
            {notes.map((c) => <li key={c.key}>{c.text}</li>)}
          </ul>
        ) : null}
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
      <section><div className="sect-h"><h3 className="h3">Severity</h3><Src tid={sev.id} n={row.values.crashes} p={data} /></div>
        <ul className="kv">{sev.rows.filter((r) => r.values.crashes).map((r) => <li key={r.key}><span>{r.label}</span><span className="mono">{fmt(r.values.crashes)}</span></li>)}</ul></section>
      <section><div className="sect-h"><h3 className="h3">Collision type</h3><Src tid={types.id} n={row.values.crashes} /></div><Bars t={types} /></section>
      <Why p={data} suffix={`@${row.key}`} n={row.values.crashes} label="Why did they crash? (this location)" h="h3" />
      <section><div className="sect-h"><h3 className="h3">Lighting</h3><Src tid={light.id} n={row.values.crashes} /></div>
        <ul className="kv">{light.rows.map((r) => <li key={r.key}><span>{r.label}</span><span className="mono">{fmt(r.values.crashes)}</span></li>)}</ul></section>
      {data.diagram ? (() => {
        const t21 = data.tables.find((x) => x.id.startsWith('T21@'))
        return <N10Diagram d={data.diagram} t={t21} label={row.label} src={t21 ? <Src tid={t21.id} n={t21.rows.length} /> : null} />
      })() : null}
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
      <div className="sect-h"><h2 className="h3">Where along the corridor crashes bunch up</h2><Src tid="T2" n={cell(p, 'T1/crashes/value')} p={p} /></div>
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
            {/* #269: the first screen answers where, how bad and can I trust it; the rest follows in this order */}
            <Kpis p={p} />
            <Quality p={p} excluded={state.excludedByRule || {}} onReview={openReview} />
            <Ranking p={p} onOpen={openLocation} />
            <Vru p={p} onMap={setMapMode} mapMode={mapMode} />
            <Strip p={p} net={state.net} crashes={state.crashes || []} onOpen={openLocation} />
            <ShsRates p={p} />
            <ShsRamps p={p} />
            <Grid p={p} onOpen={openLocation} />
            <Severity p={p} />
            <Why p={p} n={cell(p, 'T1/crashes/value')} />
            <Trend p={p} />
            <When p={p} />
            <Conditions p={p} n={cell(p, 'T1/crashes/value')} />
            <DataSources p={p} pull={state.pull} onRefresh={refresh} busy={refreshing} />
            {state.refreshError ? <div className="err" role="alert">{state.refreshError}</div> : null}
            <div className="cta-bar"><button type="button" className="sf-btn sf-btn--go" onClick={() => navigate(`/s/${studyId}/findings`)}>See findings →</button></div>
          </>
        ))}
      </div>
    </section>
  )
}
