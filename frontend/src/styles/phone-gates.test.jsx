import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TopBar from '../components/TopBar'
import Rail from '../components/Rail'
import css from './phone-gates.css?raw'

// Vitest uses jsdom with CSS processing off. Inject the real CSS for computed
// hit-target assertions. jsdom does not calculate mobile layout or media
// queries, so the 390px declarations are separately inspected via CSSOM.
let style
beforeEach(() => {
  style = document.createElement('style')
  style.textContent = css
  document.head.append(style)
})
afterEach(() => {
  cleanup()
  style.remove()
})
const target = (node) => expect(parseFloat(getComputedStyle(node).minHeight)).toBeGreaterThanOrEqual(44)

describe('CrashIQ phone conformance', () => {
  it('gives the header and study rail links at least 44px targets', () => {
    render(<MemoryRouter><TopBar projectName="Test project" /><Rail studyId="s1" current={2} reached={3} /></MemoryRouter>)
    target(document.querySelector('.top .brand'))
    target(document.querySelector('.top .toplink'))
    const steps = document.querySelectorAll('.rail a.step')
    expect(steps).toHaveLength(5)
    steps.forEach(target)
  })

  it('gives corridor search, removal, and the checkbox label 44px targets', () => {
    const { container } = render(
      <section className="corridor">
        <div className="toolbar">
          <div className="search"><input className="input" aria-label="Find a place" /></div>
          <button type="button" className="tool">Clear line</button>
        </div>
        <aside className="side">
          <div className="loc">
            <button type="button" className="n">Intersection name</button>
            <div className="acts">
              <label className="loc-check">
                <input type="checkbox" aria-label="Study intersection" />
              </label>
              <button type="button" className="x">Remove intersection</button>
            </div>
          </div>
        </aside>
      </section>,
    )
    for (const selector of ['.corridor .search .input', '.corridor .tool', '.side .loc .n', '.side .loc-check', '.side .loc .x']) {
      target(container.querySelector(selector))
    }
    expect(container.querySelector('.loc-check').contains(container.querySelector('input[type="checkbox"]'))).toBe(true)
  })

  it('enlarges profile map filters and keeps off-chip text at full opacity', () => {
    const { container } = render(
      <div className="profile">
        <button type="button" className="tbtn">Fit</button>
        <div className="map-legend2">
          <div className="seg"><button type="button">Severity</button></div>
          <button type="button" className="chip off" aria-pressed="false">Filtered</button>
          <button type="button" className="link">Clear filters</button>
        </div>
      </div>,
    )
    for (const selector of ['.tbtn', '.seg button', '.chip.off', '.link']) target(container.querySelector(selector))
    expect(getComputedStyle(container.querySelector('.chip.off')).opacity).toBe('1')
  })

  it('provides 390px wrap rules for map tools, findings and profile labels', () => {
    const mobile = Array.from(style.sheet.cssRules).find((r) => r.media?.mediaText?.includes('480px'))
    expect(mobile).toBeDefined()
    const rule = (selector) => Array.from(mobile.cssRules).find((r) => r.selectorText?.split(',').map((s) => s.trim()).includes(selector))
    expect(rule('.corridor .toolbar').style.flexWrap).toBe('wrap')
    expect(rule('.findings-screen .fcard .tt').style.whiteSpace).toBe('normal')
    expect(rule('.profile .bar .lab').style.textOverflow).toBe('clip')
    expect(rule('.profile .sf-kpis.n3').style.gridTemplateColumns).toContain('repeat(2')
  })
})
