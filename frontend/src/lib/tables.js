// Read-only helpers over the C6 profile response. The frontend formats numbers; it never computes them.
export const table = (profile, id) => profile?.tables?.find((t) => t.id === id) || null

export function cell(profile, address) {
  const [tid, row, col] = address.split('/')
  const t = table(profile, tid)
  const r = t?.rows.find((x) => x.key === row)
  return r ? r.values[col] : undefined
}

const nf = new Intl.NumberFormat('en-US')
export function fmt(v, digits) {
  if (v === null || v === undefined) return '—'
  if (typeof v !== 'number') return String(v)
  return digits === undefined ? nf.format(v) : v.toFixed(digits)
}

export const titleCase = (s) => (s || '').toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase())

// How the backend writes a number into a finding: integers bare, everything else with one decimal.
export const fmtNum = (v) => (Number.isInteger(v) ? String(v) : Number(v).toFixed(1))
