import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { AppRoutes } from './App'

// Mock fetch by route: { 'GET /studies/meta': body | (req) => body, ... }. Unknown routes → 404.
export function mockApi(routes) {
  const calls = []
  const fetchMock = vi.fn(async (url, opts = {}) => {
    const method = (opts.method || 'GET').toUpperCase()
    const path = String(url).replace(/^\/api/, '').split('?')[0]
    const body = opts.body ? JSON.parse(opts.body) : undefined
    calls.push({ method, path, body })
    const key = Object.keys(routes).find((k) => {
      const [m, p] = k.split(' ')
      if (m !== method) return false
      const re = new RegExp('^' + p.replace(/:[^/]+/g, '[^/]+') + '$')
      return re.test(path)
    })
    if (!key) return new Response(JSON.stringify({ detail: 'not found' }), { status: 404 })
    const v = routes[key]
    const out = typeof v === 'function' ? v({ method, path, body }) : v
    return new Response(JSON.stringify(out), { status: 200, headers: { 'Content-Type': 'application/json' } })
  })
  globalThis.fetch = fetchMock
  return calls
}

export function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

export const META = {
  states: [{ code: 'CA', name: 'California', ready: true }, { code: 'TX', name: 'Texas', ready: false }],
  state: 'CA', state_name: 'California', source_short: 'CCRS', severity_note: null,
  short_window_note: 'Under 3 years of crashes. Caltrans recommends at least 3, preferably 5.',
  modes: [
    { id: 'profile', label: 'Crash profile / corridor screening' },
    { id: 'tis', label: 'Traffic-study safety section' },
  ],
  default_mode: 'profile',
  default_window: { from_year: 2021, to_year: 2025 },
  window_options: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => ({
    years: n, from_year: 2026 - n, to_year: 2025, covid: 2026 - n <= 2021, short: n < 3,
    label: `Last ${n} year${n > 1 ? 's' : ''} (${n > 1 ? `${2026 - n}–2025` : '2025'})`,
  })),
  first_year: 2016, last_year: 2026, min_years: 1, max_years: 10,
}
