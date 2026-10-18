import { useEffect, useMemo } from 'react'
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { TILE_ATTR, TILE_MAX_NATIVE_ZOOM, TILE_URL } from '../lib/tiles'

const token = (n, fb) => (typeof document !== 'undefined'
  && getComputedStyle(document.documentElement).getPropertyValue(n).trim()) || fb

function FitLine({ line }) {
  const map = useMap()
  useEffect(() => {
    if (line?.length >= 2) map.fitBounds(line, { padding: [50, 50] })
  }, [line, map])
  return null
}

const SEV_ORDER = { O: 0, U: 1, C: 1, B: 1, A: 2, K: 3 }

// Severity-colored crash map: the one loud element on the profile screen.
export default function ProfileMap({ line, crashes = [], highlight }) {
  const c = useMemo(() => ({
    K: token('--sev-k', '#FF5A4E'), A: token('--sev-a', '#FF8A3D'), I: token('--sev-i', '#FFB020'),
    O: token('--sev-p', '#8E9AA6'), go: token('--go', '#1EE39A'), fg: token('--fg', '#E6EAEE'),
  }), [])
  const color = (s) => (s === 'K' ? c.K : s === 'A' ? c.A : s === 'O' ? c.O : c.I)
  // draw property-damage crashes first so injuries sit on top
  const pts = useMemo(() => crashes.filter((x) => x.lat != null && x.lon != null)
    .sort((a, b) => SEV_ORDER[a.severity] - SEV_ORDER[b.severity]), [crashes])

  return (
    <MapContainer center={line?.[0] || [34, -118.3]} zoom={15} zoomControl={false} className="ciq-map" preferCanvas>
      <TileLayer url={TILE_URL} attribution={TILE_ATTR} maxNativeZoom={TILE_MAX_NATIVE_ZOOM} maxZoom={20} />
      <FitLine line={line} />
      {line ? <Polyline positions={line} pathOptions={{ color: c.go, weight: 5, opacity: 0.35 }} interactive={false} /> : null}
      {pts.map((x) => {
        const on = !highlight || highlight.has(x.crash_id)
        return (
          <CircleMarker key={x.crash_id} center={[x.lat, x.lon]} radius={x.severity === 'K' || x.severity === 'A' ? 6 : 4}
            pathOptions={{ color: on ? color(x.severity) : c.O, fillColor: color(x.severity), weight: 1,
              fillOpacity: on ? 0.85 : 0.12, opacity: on ? 1 : 0.2 }}>
            <Tooltip>{`${x.collision_type || 'Crash'} · ${x.date}${x.hour != null ? ` · ${String(x.hour).padStart(2, '0')}:00` : ''}`}</Tooltip>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
