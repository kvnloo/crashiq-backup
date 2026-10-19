import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { META, mockApi, renderAt } from '../test-utils'

describe('Setup', () => {
  it('offers exactly the two v1 modes, nothing marked "coming soon"', async () => {
    mockApi({ 'GET /studies/meta': META })
    renderAt('/')
    const select = await screen.findByLabelText('Study')
    await waitFor(() => expect(select.querySelectorAll('option')).toHaveLength(2))
    expect(Array.from(select.options).map((o) => o.textContent)).toEqual([
      'Crash profile / corridor screening', 'Traffic-study safety section'])
    expect(screen.queryByText(/coming/i)).toBeNull()
  })

  it('defaults to the last 5 complete years and has a custom range option', async () => {
    mockApi({ 'GET /studies/meta': META })
    renderAt('/')
    const years = await screen.findByLabelText('Crash history')
    await waitFor(() => expect(years.value).toBe('5'))
    expect(years.options[years.selectedIndex].textContent).toBe('Last 5 years (2021–2025)')
    expect(Array.from(years.options).at(-1).textContent).toBe('Custom range')
  })

  it('flags a window that includes 2020 or 2021', async () => {
    mockApi({ 'GET /studies/meta': META })
    renderAt('/')
    const years = await screen.findByLabelText('Crash history')
    await waitFor(() => expect(years.value).toBe('5'))
    expect(screen.getByText(/Includes 2020 or 2021/)).toBeInTheDocument()     // 2021–2025 touches 2021
    fireEvent.change(years, { target: { value: '4' } })                       // 2022–2025
    expect(screen.queryByText(/COVID/)).toBeNull()
  })

  it('creates the study with the chosen window and one primary action', async () => {
    const calls = mockApi({
      'GET /studies/meta': META,
      'POST /studies': (req) => ({ id: 'new1', ...req.body }),
      'GET /studies/:id': { id: 'new1', name: 'Crenshaw', mode: 'tis', from_year: 2021, to_year: 2025 },
    })
    renderAt('/')
    await screen.findByLabelText('Crash history')
    fireEvent.change(screen.getByLabelText('Project'), { target: { value: 'Crenshaw' } })
    fireEvent.change(screen.getByLabelText('Study'), { target: { value: 'tis' } })
    expect(screen.getAllByRole('button')).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Draw the corridor →' }))
    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true))
    const post = calls.find((c) => c.method === 'POST')
    expect(post.body).toEqual({ name: 'Crenshaw', mode: 'tis', from_year: 2021, to_year: 2025 })
  })

  it('warns when the window is under 3 years', async () => {
    mockApi({ 'GET /studies/meta': META })
    renderAt('/')
    fireEvent.change(await screen.findByLabelText('Crash history'), { target: { value: '2' } })
    expect(screen.getByText(/Under 3 years of crashes/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Crash history'), { target: { value: '5' } })
    expect(screen.queryByText(/Under 3 years of crashes/)).toBeNull()
  })
})
