import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useMemo, useRef, useState } from 'react'
import { DIMENSIONS, categories, catOf, columns, corridorAzimuth, topLocations, visible } from '../lib/mapcats'
import { TILE_MAX_NATIVE_ZOOM, TILE_URL } from '../lib/tiles'

const TILE_ATTR_HTML = 'Tiles © Esri — Esri, HERE, Garmin, © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
const PITCH_3D = 55
const EMPTY = { type: 'FeatureCollection', features: [] }
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (ch) => `&#${ch.charCodeAt(0)};`)
const round = (b) => Math.round(((b % 360) + 540) % 360 - 180)

function style() {
  return {
    version: 8,
    sources: {
      base: { type: 'raster', tiles: [TILE_URL], tileSize: 256, maxzoom: TILE_MAX_NATIVE_ZOOM, attribution: TILE_ATTR_HTML },
      corridor: { type: 'geojson', data: EMPTY },
      crashes: { type: 'geojson', data: EMPTY },
      columns: { type: 'geojson', data: EMPTY },
      locs: { type: 'geojson', data: EMPTY },
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#14181C' } },
      // dimmed so the data reads first (#100); street names come from our own labels and hovers
      { id: 'base', type: 'raster', source: 'base', paint: { 'raster-opacity': 0.55, 'raster-saturation': -0.6 } },
      { id: 'corridor', type: 'line', source: 'corridor', paint: { 'line-color': '#1EE39A', 'line-width': 5, 'line-opacity': 0.35 },
        layout: { 'line-cap': 'round' } },
      // invisible hover targets: every location's name and crash count on hover (#100)
      { id: 'locs', type: 'circle', source: 'locs', paint: { 'circle-radius': 14, 'circle-opacity': 0.01,
        'circle-pitch-alignment': 'map' } },
      { id: 'crashes', type: 'circle', source: 'crashes', paint: {
        'circle-color': ['get', 'color'], 'circle-radius': ['case', ['get', 'big'], 6, 4.5],
        'circle-opacity': ['case', ['get', 'dim'], 0.15, 0.9], 'circle-stroke-color': '#0D1013',
        'circle-stroke-width': 1.5, 'circle-stroke-opacity': ['case', ['get', 'dim'], 0.2, 1], 'circle-pitch-alignment': 'map' } },
      { id: 'columns', type: 'fill-extrusion', source: 'columns', paint: {
        'fill-extrusion-color': ['get', 'color'], 'fill-extrusion-base': ['get', 'base'], 'fill-extrusion-height': ['get', 'top'],
        'fill-extrusion-opacity': 0.92 } },
    ],
  }
}

// Crash map for step 3. 3D view: one stacked column per location (height = crashes, slabs = the "color by"
// categories); 2D view: dots only. Rotate/tilt with the buttons, right-drag, or two fingers.
export default function ProfileMap({ line, crashes = [], locations = [], highlight, onPick, selected }) {
  const box = useRef(null)
  const mapRef = useRef(null)
  const pickRef = useRef(onPick)
  const [ready, setReady] = useState(false)
  const [dim, setDim] = useState('severity')
  const [hidden, setHidden] = useState({})
  const [is3d, setIs3d] = useState(true)
  const [bearing, setBearing] = useState(0)

  const cats = useMemo(() => categories(dim, crashes), [dim, crashes])
  const colorOf = useMemo(() => new Map(cats.map((c) => [c.key, c.color])), [cats])
  const shown = useMemo(() => crashes.filter((c) => visible(c, hidden)), [crashes, hidden])
  const counts = useMemo(() => {
    const m = new Map()
    for (const c of crashes.filter((x) => visible(x, { ...hidden, [dim]: null }))) {
      const k = catOf(dim, c); m.set(k, (m.get(k) || 0) + 1)
    }
    return m
  }, [crashes, hidden, dim])
  // default view: the corridor runs diagonally up the screen, so columns along it don't hide each other
  const align = useMemo(() => round(corridorAzimuth(line) - 45), [line])
  // columns scale with the corridor so they read at the fitted zoom: tallest ≈ 1/5 of the corridor length
  const scale = useMemo(() => {
    if (!line || line.length < 2) return { h: 220, r: 14 }
    const [a, b] = [line[0], line[line.length - 1]]
    const m = Math.hypot((b[0] - a[0]) * 111320, (b[1] - a[1]) * 111320 * Math.cos((a[0] * Math.PI) / 180))
    return { h: Math.max(120, m / 5), r: Math.max(10, m / 90) }
  }, [line])

  // create the map once
  useEffect(() => {
    if (!box.current) return undefined
    let map
    try {
      map = new maplibregl.Map({ container: box.current, style: style(), center: [-118.3, 34], zoom: 14,
        pitch: PITCH_3D, maxPitch: 70, attributionControl: { compact: true }, dragRotate: true, touchPitch: true })
    } catch {
      return undefined                      // no WebGL: the legend and tables still work
    }
    mapRef.current = map
    // Our layers need only the style, not basemap tiles: don't wait for 'load', which a tile outage can hold back.
    const onStyle = () => { if (map.getSource('crashes')) setReady(true) }
    map.on('style.load', onStyle)
    map.on('load', onStyle)
    map.on('idle', onStyle)
    map.on('error', () => {})              // a missing basemap tile must not spam the console or block the layers
    map.on('rotate', () => setBearing(map.getBearing()))
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: 'ciq-pop' })
    map.on('mousemove', 'crashes', (e) => {
      const p = e.features?.[0]?.properties
      if (!p) return
      map.getCanvas().style.cursor = 'pointer'
      popup.setLngLat(e.lngLat).setHTML(`<b>${esc(p.type)}</b><br>${esc(p.date)}${p.hour ? ` · ${esc(p.hour)}` : ''} · ${esc(p.sev)}`).addTo(map)
    })
    map.on('mousemove', 'columns', (e) => {
      const p = e.features?.[0]?.properties
      if (!p) return
      popup.setLngLat(e.lngLat).setHTML(`<b>${esc(p.location)}</b><br>${esc(p.count)} ${esc(String(p.cat).toLowerCase())} · ${esc(p.total)} crashes here`).addTo(map)
    })
    map.on('mousemove', 'locs', (e) => {
      const p = e.features?.[0]?.properties
      if (!p || map.queryRenderedFeatures(e.point, { layers: ['columns', 'crashes'] }).length) return
      popup.setLngLat(e.lngLat).setHTML(`<b>${esc(p.location)}</b><br>${esc(p.total)} crash${p.total === 1 ? '' : 'es'}`).addTo(map)
    })
    for (const l of ['crashes', 'columns', 'locs']) map.on('mouseleave', l, () => { map.getCanvas().style.cursor = ''; popup.remove() })
    return () => { popup.remove(); map.remove(); mapRef.current = null }
  }, [])

  // review list (#97): while a point is being picked, the next map click returns it
  useEffect(() => {
    pickRef.current = onPick
    const map = mapRef.current
    if (!ready || !map || !onPick) return undefined
    map.getCanvas().style.cursor = 'crosshair'
    const click = (e) => pickRef.current?.({ lat: e.lngLat.lat, lon: e.lngLat.lng })
    map.on('click', click)
    return () => { map.off('click', click); map.getCanvas().style.cursor = '' }
  }, [ready, onPick])

  // fit the corridor, laid across the screen, once the map and line are ready
  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map || !line?.length) return
    map.getSource('corridor').setData({ type: 'Feature', geometry: { type: 'LineString', coordinates: line.map(([la, lo]) => [lo, la]) } })
    fit(false)
  }, [ready, line, align]) // eslint-disable-line react-hooks/exhaustive-deps

  // data layers follow the filters and the "color by" choice
  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map) return
    map.getSource('crashes').setData({ type: 'FeatureCollection', features: shown.filter((c) => c.lat != null && c.lon != null).map((c) => ({
      type: 'Feature', geometry: { type: 'Point', coordinates: [c.lon, c.lat] },
      properties: { color: colorOf.get(catOf(dim, c)) || '#6B7682', dim: Boolean(highlight && !highlight.has(c.crash_id)),
        big: c.severity === 'K' || c.severity === 'A', type: (c.collision_type || 'Crash').toLowerCase(), date: c.date || '',
        hour: c.hour != null ? `${String(c.hour).padStart(2, '0')}:00` : '', sev: c.severity },
    })) })
    map.getSource('columns').setData(is3d ? columns(locations, shown, dim, cats, scale.h, scale.r) : EMPTY)
  }, [ready, shown, dim, cats, colorOf, locations, is3d, highlight, scale])

  // Names as HTML markers (no glyph server needed), but only for the 3 locations with the most crashes and the one
  // opened in the drill-down; every other name and every count is on hover (#100: the user found it cluttered).
  const labelled = useMemo(() => new Set([...topLocations(locations, shown), ...(selected ? [selected] : [])]),
    [locations, shown, selected])
  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map) return
    const n = new Map()
    for (const c of shown) if (c.location_id) n.set(c.location_id, (n.get(c.location_id) || 0) + 1)
    map.getSource('locs').setData({ type: 'FeatureCollection', features: locations.map((l) => ({
      type: 'Feature', geometry: { type: 'Point', coordinates: [l.lon, l.lat] },
      properties: { location: l.name, total: n.get(l.id) || 0 },
    })) })
  }, [ready, locations, shown])
  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map) return undefined
    const ms = locations.filter((l) => labelled.has(l.id)).map((l) => {
      const el = document.createElement('div')
      el.className = 'ciq-label'
      el.textContent = l.name
      return new maplibregl.Marker({ element: el, anchor: 'top', offset: [0, 10] }).setLngLat([l.lon, l.lat]).addTo(map)
    })
    return () => ms.forEach((m) => m.remove())
  }, [ready, locations, labelled])

  function fit(animate) {
    const map = mapRef.current
    if (!map || !line?.length) return
    const lons = line.map((p) => p[1]), lats = line.map((p) => p[0])
    const cam = map.cameraForBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
      { padding: { top: 70, bottom: 170, left: 50, right: 50 }, bearing: align })
    if (!cam) return
    // tilting pushes the near end of the corridor toward the edge; back off a little in 3D
    const v = { ...cam, zoom: cam.zoom - (is3d ? 0.4 : 0), bearing: align, pitch: is3d ? PITCH_3D : 0 }
    if (animate) map.easeTo({ ...v, duration: 700 }); else map.jumpTo(v)
  }

  const ease = (o) => mapRef.current?.easeTo({ duration: 600, ...o })
  const toggle = (k) => setHidden((h) => {
    const s = new Set(h[dim] || [])
    if (s.has(k)) s.delete(k); else s.add(k)
    return { ...h, [dim]: s }
  })
  const nFilters = Object.values(hidden).reduce((a, s) => a + (s?.size || 0), 0)

  return (
    <div className="pmap">
      <div ref={box} className="ciq-map" data-testid="profile-map" />
      <div className="float map-tools" role="toolbar" aria-label="Map view">
        <button type="button" className={`tbtn${is3d ? ' on' : ''}`} aria-pressed={is3d}
          onClick={() => { setIs3d(!is3d); ease({ pitch: is3d ? 0 : PITCH_3D }) }}>{is3d ? '3D' : '2D'}</button>
        <button type="button" className="tbtn" aria-label="Rotate left" title="Rotate left" onClick={() => ease({ bearing: bearing - 45 })}>⟲</button>
        <button type="button" className="tbtn compass" aria-label={`Reset north (now ${round(bearing)}°)`} title="North up"
          onClick={() => ease({ bearing: 0 })}><svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" style={{ transform: `rotate(${-bearing}deg)` }}>
            <path d="M8 1 L11 8 H5 Z" fill="var(--stop)" /><path d="M8 15 L5 8 H11 Z" fill="var(--muted)" /></svg></button>
        <button type="button" className="tbtn" aria-label="Rotate right" title="Rotate right" onClick={() => ease({ bearing: bearing + 45 })}>⟳</button>
        <button type="button" className="tbtn wide" title="Back to the default view of the whole corridor" onClick={() => fit(true)}>Fit</button>
      </div>
      <div className="float map-legend2" aria-label="Map legend and filters">
        <div className="seg" role="radiogroup" aria-label="Color by">
          {DIMENSIONS.map((d) => (
            <button key={d.key} type="button" role="radio" aria-checked={dim === d.key} className={dim === d.key ? 'on' : ''}
              onClick={() => setDim(d.key)}>{d.label}</button>
          ))}
        </div>
        <div className="chips">
          {cats.map((c) => {
            const off = hidden[dim]?.has(c.key)
            return (
              <button key={c.key} type="button" className={`chip${off ? ' off' : ''}`} aria-pressed={!off} onClick={() => toggle(c.key)}
                title={off ? 'Show' : 'Hide'}>
                <i style={{ background: c.color }} />{c.label}<b className="mono">{counts.get(c.key) || 0}</b>
              </button>
            )
          })}
        </div>
        <div className="foot mono">
          <span>Showing {shown.length} of {crashes.length} crashes{is3d ? ' · column height = crashes at the location' : ''}</span>
          {nFilters ? <button type="button" className="link" onClick={() => setHidden({})}>Clear {nFilters} filter{nFilters > 1 ? 's' : ''}</button> : null}
        </div>
      </div>
    </div>
  )
}
