import { useState } from 'react'
import { searchPhoton } from '../lib/photon'

// Jump the map to a place ("Crenshaw Blvd, Hawthorne"). Photon geocoder, no key.
export default function PlaceSearch({ onPick }) {
  const [q, setQ] = useState('')
  const [hits, setHits] = useState([])
  const [msg, setMsg] = useState('')

  async function search(e) {
    e.preventDefault()
    if (!q.trim()) return
    setMsg('')
    try {
      const r = await searchPhoton(q.trim())
      setHits(r)
      if (!r.length) setMsg('No places found.')
    } catch {
      setMsg("Search isn't available right now. Pan the map instead.")
    }
  }

  return (
    <form className="search" onSubmit={search} role="search">
      <input className="input" aria-label="Find a place" placeholder="Find a street or city" value={q}
        onChange={(e) => setQ(e.target.value)} />
      {(hits.length > 0 || msg) && (
        <div className="hits">
          {msg ? <div className="muted">{msg}</div> : null}
          {hits.map((h) => (
            <button type="button" key={`${h.lat},${h.lng},${h.label}`}
              onClick={() => { onPick([h.lat, h.lng]); setHits([]); setQ(h.label) }}>{h.label}</button>
          ))}
        </div>
      )}
    </form>
  )
}
