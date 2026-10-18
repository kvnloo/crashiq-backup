// The five study steps (docs/03-requirements.md R7, user decision 2026-10-18).
export const STEPS = [
  { key: 'setup', label: 'Setup' },
  { key: 'corridor', label: 'Corridor' },
  { key: 'profile', label: 'Crash profile' },
  { key: 'findings', label: 'Findings' },
  { key: 'export', label: 'Export' },
]

export const stepPath = (studyId, key) => (studyId ? `/s/${studyId}/${key}` : '/')
