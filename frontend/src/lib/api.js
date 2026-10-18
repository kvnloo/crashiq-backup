// Tiny fetch wrapper. Errors carry the server's `detail` so screens can show a plain message.
export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : 'Request failed')
    this.status = status
    this.detail = detail
  }
}

export async function api(path, { method = 'GET', body, signal } = {}) {
  const res = await fetch(`/api${path}`, {
    method,
    signal,
    credentials: 'same-origin',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  const text = await res.text()
  let data
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!res.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : data
    throw new ApiError(res.status, detail || `${res.status} ${res.statusText}`)
  }
  return data
}

// Human message for any error thrown by api(): FastAPI validation errors arrive as a list.
export function errorText(err) {
  if (!err) return ''
  const d = err.detail
  if (Array.isArray(d)) return d.map((x) => x.msg || String(x)).join('; ')
  return err.message || String(err)
}
