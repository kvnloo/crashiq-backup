import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { META, mockApi, renderAt } from '../test-utils'
import profile from '../__fixtures__/profile.json'
import { cell } from '../lib/tables'

const STUDY = { id: 's1', name: 'Crenshaw', mode: 'tis', from_year: 2021, to_year: 2025, radius_ft: 250, buffer_ft: 100 }

describe('Export screen', () => {
  it('offers PDF and Excel and counts the files on the one primary button', async () => {
    mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': STUDY, 'GET /studies/:id/profile': profile })
    renderAt('/s/s1/export')
    const btn = await screen.findByRole('button', { name: 'Export 2 files ↓' })
    await waitFor(() => expect(btn).toBeEnabled())
    fireEvent.click(screen.getByLabelText(/Excel workbook/))
    expect(screen.getByRole('button', { name: 'Export 1 file ↓' })).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText(/PDF report/))
    expect(screen.getByRole('button', { name: 'Choose a file' })).toBeDisabled()
    expect(document.querySelectorAll('.sf-btn--go')).toHaveLength(1)
  })

  it('previews show the real profile numbers', async () => {
    mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': STUDY, 'GET /studies/:id/profile': profile })
    renderAt('/s/s1/export')
    await screen.findByRole('button', { name: 'Export 2 files ↓' })
    const n = new Intl.NumberFormat('en-US').format(cell(profile, profile.kpis.crashes))
    await waitFor(() => expect(document.querySelector('.page .kp').textContent).toContain(n))
  })
})

describe('Rail progress', () => {
  it('checks off Corridor and Crash profile once the study has crashes', async () => {
    mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': { ...STUDY, progress: { corridor: true, crashes: true } },
      'GET /studies/:id/profile': profile })
    renderAt('/s/s1/export')
    await waitFor(() => expect(document.querySelectorAll('.rail .step.done')).toHaveLength(4))
  })

  it('checks off only Setup before a corridor is drawn', async () => {
    mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': { ...STUDY, progress: { corridor: false, crashes: false } },
      'GET /studies/:id/profile': profile })
    renderAt('/s/s1/export')
    await screen.findByRole('button', { name: 'Export 2 files ↓' })
    expect(document.querySelectorAll('.rail .step.done')).toHaveLength(1)
  })
})
