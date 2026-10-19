import { useEffect, useMemo, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { MapboxOverlay } from '@deck.gl/mapbox'
import { ColumnLayer, PathLayer, ScatterplotLayer } from '@deck.gl/layers'
import ProfileMap from './ProfileMap'
import { TILE_ATTR, TILE_MAX_NATIVE_ZOOM, TILE_URL } from '../lib/tiles'
import { locationPoints } from '../lib/locationPoints'

// The profile's one loud element (design/principles.md #4): a tilted map with one column per location.
// Column height = crashes and color = injury/KSI share, both straight from the profile API's T2 rows; this
// component computes positions only, never a number the user reads. Falls back to the flat map without WebGL.

const token = (n, fb) => (typeof document !== 'undefined'
  && getComputedStyle(document.documentElement).getPropertyValue(n).trim()) || fb
const rgb = (hex, a = 255) => {
  const n = parseInt(hex.replace('#', ''), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255, a]
}
const reduced = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
// Display scale only: the tallest column is ~30% of the corridor's length, so it reads at any zoom.
const TALLEST_SHARE = 0.3

function webglOk() {
  try {
    const c = document.createElement('canvas')
    return Boolean(c.getContext('webgl2') || c.getContext('webgl'))
  } catch { return false }
}

const STYLE = {
  version: 8,
  sources: { base: { type: 'raster', tiles: [TILE_URL], tileSize: 256,
    maxzoom: TILE_MAX_NATIVE_ZOOM, attribution: TILE_ATTR } },
  layers: [{ id: 'base', type: 'raster', source: 'base' }],
}

export default function ProfileMap3D({ line, net, locations, crashes = [], highlight }) {
  const [ok] = useState(webglOk)
  const box = useRef(null)
  const mapRef = useRef(null)
  const overlayRef = useRef(null)
  const [grow, setGrow] = useState(reduced() ? 1 : 0)

  const c = useMemo(() => ({
    K: token('--sev-k', '#FF5A4E'), A: token('--sev-a', '#FF8A3D'), I: token('--sev-i', '#FFB020'),
    O: token('--sev-p', '#8E9AA6'), go: token('--go', '#1EE39A'), bg: token('--bg', '#0D1013'),
  }), [])
  const pts = useMemo(() => locationPoints(locations, net), [locations, net])
  const metresPerCrash = useMemo(() => {
    if (!line?.length || !pts.length) return 18
    const r = 6371000, rad = Math.PI / 180
    let len = 0
    for (let i = 1; i < line.length; i++) {
      const [a, b] = [line[i - 1], line[i]]
      const x = (b[1] - a[1]) * rad * Math.cos(((a[0] + b[0]) / 2) * rad), y = (b[0] - a[0]) * rad
      len += Math.hypot(x, y) * r
    }
    return (len * TALLEST_SHARE) / Math.max(...pts.map((d) => d.crashes))
  }, [line, pts])
  const dots = useMemo(() => crashes.filter((x) => x.lat != null && x.lon != null), [crashes])

  // map once
  useEffect(() => {
    if (!ok || !box.current || !line?.length) return undefined
    const map = new maplibregl.Map({ container: box.current, style: STYLE, center: [line[0][1], line[0][0]], zoom: 15,
      pitch: 55, bearing: -20, maxPitch: 70, attributionControl: { compact: true } })
    const overlay = new MapboxOverlay({ interleaved: false, layers: [],
      getTooltip: ({ object: o }) => o && (o.crashes != null
        ? `${o.label}\n${o.crashes} crashes · ${o.injury} injury · ${o.ksi} KSI`
        : `${o.collision_type || 'Crash'} · ${o.date}`) })
    map.addControl(overlay)
    const lons = line.map((p) => p[1]); const lats = line.map((p) => p[0])
    const fit = () => map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
      { padding: 70, pitch: 55, bearing: -20, duration: 0 })
    fit()
    // the panel settles after first paint (and on window resize): keep the canvas filling it
    const ro = new ResizeObserver(() => { map.resize(); fit() })
    ro.observe(box.current)
    mapRef.current = map
    overlayRef.current = overlay
    return () => { ro.disconnect(); map.remove(); mapRef.current = null; overlayRef.current = null }
  }, [ok, line])

  // columns rise in once per load
  useEffect(() => {
    if (!ok || reduced()) return undefined
    let raf = 0; const t0 = performance.now()
    const tick = (now) => { const k = Math.min(1, (now - t0) / 1200); setGrow(1 - (1 - k) ** 3); if (k < 1) raf = requestAnimationFrame(tick) }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [ok, pts])

  useEffect(() => {
    if (!overlayRef.current) return
    const sevColor = (s) => rgb(s === 'K' ? c.K : s === 'A' ? c.A : s === 'O' ? c.O : c.I)
    const colColor = (d) => rgb(d.ksi > 0 ? c.K : d.injury / d.crashes >= 0.4 ? c.I : c.O, d.seg ? 150 : 235)
    overlayRef.current.setProps({ layers: [
      new PathLayer({ id: 'corridor', data: [{ path: line.map((p) => [p[1], p[0]]) }], getPath: (d) => d.path,
        getColor: rgb(c.go, 110), getWidth: 8, widthUnits: 'pixels', capRounded: true }),
      new ScatterplotLayer({ id: 'crashes', data: dots, pickable: true, getPosition: (d) => [d.lon, d.lat],
        getRadius: 3, radiusUnits: 'pixels', getFillColor: (d) => sevColor(d.severity).map((v, i) =>
          (i === 3 && highlight && !highlight.has(d.crash_id) ? 40 : v)),
        updateTriggers: { getFillColor: [highlight] } }),
      new ColumnLayer({ id: 'locations', data: pts, pickable: true, extruded: true, diskResolution: 24,
        radius: 30, getPosition: (d) => d.pos, getElevation: (d) => d.crashes * metresPerCrash * grow,
        getFillColor: colColor, material: { ambient: 0.55, diffuse: 0.6, shininess: 24 },
        updateTriggers: { getElevation: [grow, metresPerCrash] } }),
    ] })
  }, [pts, dots, line, grow, highlight, c, metresPerCrash])

  if (!ok) return <ProfileMap line={line} crashes={crashes} highlight={highlight} />
  return <div ref={box} className="ciq-map ciq-map3d" data-testid="map3d" aria-label="3D crash map" />
}
