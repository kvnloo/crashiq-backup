import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { META, mockApi, renderAt } from './test-utils'

beforeEach(() => {
  mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': { id: 'abc', name: 'Crenshaw', mode: 'profile', from_year: 2021, to_year: 2025 } })
})

describe('app shell', () => {
  it('shows the five steps in order, titles only', () => {
    renderAt('/')
    const rail = screen.getByRole('navigation', { name: 'Study steps' })
    const labels = Array.from(rail.querySelectorAll('.step .t')).map((n) => n.textContent)
    expect(labels).toEqual(['Setup', 'Corridor', 'Crash profile', 'Findings', 'Export'])
  })

  it('has the static logo and the required data credit, no theme toggle or example badge', () => {
    renderAt('/')
    expect(screen.getByLabelText('CrashIQ home')).toBeInTheDocument()
    expect(screen.queryByText(/example data/i)).toBeNull()
    expect(screen.queryByLabelText(/theme/i)).toBeNull()
    const rail = screen.getByRole('navigation', { name: 'Study steps' })
    expect(within(rail).getByText(/CCRS \(CHP\)/)).toBeInTheDocument()
    expect(within(rail).getByText(/OpenStreetMap contributors/)).toBeInTheDocument()
  })

  it('keeps later steps closed until a study exists', () => {
    renderAt('/')
    const rail = screen.getByRole('navigation', { name: 'Study steps' })
    expect(within(rail).getAllByRole('link')).toHaveLength(1) // only Setup
  })

  it('opens every step once a study exists, marks the current one, shows the project name', async () => {
    renderAt('/s/abc/profile')
    const rail = screen.getByRole('navigation', { name: 'Study steps' })
    expect(within(rail).getAllByRole('link')).toHaveLength(5)
    expect(within(rail).getByRole('link', { current: 'step' })).toHaveTextContent('Crash profile')
    expect(await screen.findByText('Crenshaw')).toBeInTheDocument()
  })
})
