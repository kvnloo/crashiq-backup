import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { mockApi, renderAt } from '../test-utils'

const REFS = {
  updated: '2026-10-18', note: 'Every method and its source.',
  sources: {
    hsm: { title: 'Highway Safety Manual, 1st Edition (2010)', publisher: 'AASHTO', url: 'https://www.highwaysafetymanual.org' },
    fhwa_ihsdm: { title: "IHSDM Crash Prediction Module Engineer's Manual, Section 2", publisher: 'FHWA', url: 'https://ihsdm.org/x' },
  },
  methods: [
    { topic: 'Intersection vs. segment crashes', status: 'follows', what: 'Within 250 ft of an intersection.',
      cite: [['fhwa_ihsdm', '250 ft rule'], ['hsm', 'Part C, Sec. C.6.2']] },
    { topic: 'Entering volume', status: 'decision', what: 'Major + minor.', cite: [['hsm', 'Ch. 4, Eq. 4-2']] },
  ],
}

describe('Methods & references page', () => {
  it('lists each method with its status and numbered citations to the sources', async () => {
    mockApi({ 'GET /references': REFS })
    renderAt('/methods')
    expect(await screen.findByText('Intersection vs. segment crashes')).toBeInTheDocument()
    expect(screen.getByText('Follows the source')).toBeInTheDocument()
    expect(screen.getByText('Engineer decision open')).toBeInTheDocument()
    const first = screen.getByText('Intersection vs. segment crashes').closest('li')
    expect(within(first).getAllByRole('link').map((a) => a.textContent)).toEqual(['[1]', '[2]'])
    const src = document.getElementById('ref-fhwa_ihsdm')
    expect(src).toHaveTextContent('[1] FHWA')
    expect(within(src).getByRole('link')).toHaveAttribute('href', 'https://ihsdm.org/x')
  })

  it('is linked from the top bar', async () => {
    mockApi({ 'GET /studies/meta': {} , 'GET /references': REFS })
    renderAt('/methods')
    expect(await screen.findByRole('link', { name: 'Methods & references' })).toHaveAttribute('href', '/methods')
  })
})
