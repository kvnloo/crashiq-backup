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

describe('Findings screen', () => {
  it('finds patterns on first visit (code only) and says plainly when none stand out', async () => {
    mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': STUDY,
      'GET /config': { ai: { claude_configured: false } }, 'GET /studies/:id/findings': { findings: [], rejected_count: 0 },
      'POST /studies/:id/findings/generate': { shown: [], rejected: [], flagged: 0 } })
    renderAt('/s/s1/findings')
    expect(await screen.findByText('No crash pattern stands out')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Go to export →' })).toHaveClass('sf-btn--go')
  })

  it('shows generated findings without needing the AI key', async () => {
    const f = { id: 'auto-osm-1-broadside', status: 'proposed', pattern_ref: 'HSM Ch. 6, right-angle collisions',
      text: 'Broadside (right-angle) crashes are over-represented at Dyer Street: 7 of 11 crashes (64%)…' }
    mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': STUDY,
      'GET /config': { ai: { claude_configured: false } }, 'GET /studies/:id/findings': { findings: [], rejected_count: 0 },
      'POST /studies/:id/findings/generate': { shown: [f], rejected: [], flagged: 1 } })
    renderAt('/s/s1/findings')
    expect(await screen.findByText(/over-represented at Dyer Street/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Accept' })).toBeInTheDocument()
  })

  it('lists validated findings with accept and reject', async () => {
    const calls = mockApi({ 'GET /studies/meta': META, 'GET /studies/:id': STUDY, 'GET /config': { ai: { claude_configured: true } },
      'GET /studies/:id/findings': { findings: [{ id: 'f1', text: 'Broadside crashes dominate at Marine Ave.', status: 'proposed' }], rejected_count: 1 },
      'PATCH /studies/:id/findings/:fid': { id: 'f1', text: 'Broadside crashes dominate at Marine Ave.', status: 'accepted' } })
    renderAt('/s/s1/findings')
    fireEvent.click(await screen.findByRole('button', { name: 'Accept' }))
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(await screen.findByText('accepted')).toBeInTheDocument()
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
