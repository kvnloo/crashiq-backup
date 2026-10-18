import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AppRoutes } from './App'

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

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

  it('opens every step once a study exists and marks the current one', () => {
    renderAt('/s/abc/profile')
    const rail = screen.getByRole('navigation', { name: 'Study steps' })
    expect(within(rail).getAllByRole('link')).toHaveLength(5)
    expect(within(rail).getByRole('link', { current: 'step' })).toHaveTextContent('Crash profile')
  })
})
