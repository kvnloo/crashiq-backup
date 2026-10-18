import { useEffect, useMemo, useRef } from 'react'
import { Circle, MapContainer, Marker, Polygon, Polyline, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { FT_TO_M, TILE_ATTR, TILE_MAX_NATIVE_ZOOM, TILE_URL } from '../lib/tiles'

const DEFAULT_CENTER = [33.9038, -118.3266]
// Leaflet writes stroke/fill as SVG attributes, so colors come from the theme tokens at render time.
const token = (n, fb) => (typeof document !== 'undefined'
  && getComputedStyle(document.documentElement).getPropertyValue(n).trim()) || fb
const DEFAULT_ZOOM = 14

const endIcon = (t) => L.divIcon({ className: 'ciq-end', html: `<span>${t}</span>`, iconSize: [26, 26], iconAnchor: [13, 13] })
const pinIcon = (n, { study, selected }) => L.divIcon({
  className: `ciq-pin${study ? '' : ' ciq-pin--off'}${selected ? ' ciq-pin--sel' : ''}`,
  html: `<span>${n}</span>`, iconSize: [24, 24], iconAnchor: [12, 12],
})

function ClickLayer({ onClick, onDoubleClick }) {
  useMapEvents({
    click: (e) => onClick?.([e.latlng.lat, e.latlng.lng]),
    dblclick: (e) => onDoubleClick?.([e.latlng.lat, e.latlng.lng]),
  })
  return null
}

// Fits the map to `points` whenever `fitKey` changes (new corridor loaded, search result picked).
function Fit({ points, fitKey, padRight }) {
  const map = useMap()
  const last = useRef(null)
  useEffect(() => {
    if (!fitKey || fitKey === last.current || !points?.length) return
    last.current = fitKey
    if (points.length === 1) map.setView(points[0], 17)
    else map.fitBounds(points, { paddingTopLeft: [60, 60], paddingBottomRight: [padRight, 60] })
  }, [fitKey, points, map, padRight])
  return null
}

function DoubleClickZoom({ enabled }) {
  const map = useMap()
  useEffect(() => {
    if (enabled) map.doubleClickZoom.enable()
    else map.doubleClickZoom.disable()
  }, [enabled, map])
  return null
}

/**
 * The corridor map. `mode`:
 *  - 'draw'   clicks add line points; double-click finishes
 *  - 'add'    a click adds an intersection at that point
 *  - 'review' A/B draggable; pins selectable
 */
export default function CorridorMap({
  mode, line, intersections = [], radiusFt = 250, bufferRing, selectedId,
  onAddPoint, onFinish, onAddIntersection, onMoveEnd, onSelect, fitKey, fitPoints, padRight = 420,
}) {
  const colors = useMemo(() => ({ go: token('--go', '#1EE39A'), fg: token('--fg', '#E6EAEE') }), [])
  const studyInts = useMemo(() => intersections.filter((i) => i.is_study), [intersections])
  const numbered = useMemo(() => {
    let n = 0
    return intersections.map((i) => ({ ...i, n: i.is_study ? ++n : '·' }))
  }, [intersections])

  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} zoomControl={false} className="ciq-map"
      doubleClickZoom={mode !== 'draw'}>
      <TileLayer url={TILE_URL} attribution={TILE_ATTR} maxNativeZoom={TILE_MAX_NATIVE_ZOOM} maxZoom={20} />
      <DoubleClickZoom enabled={mode !== 'draw'} />
      <Fit points={fitPoints} fitKey={fitKey} padRight={padRight} />
      <ClickLayer
        onClick={(p) => { if (mode === 'draw') onAddPoint?.(p); else if (mode === 'add') onAddIntersection?.(p) }}
        onDoubleClick={() => { if (mode === 'draw') onFinish?.() }}
      />
      {bufferRing ? (
        <Polygon positions={bufferRing} pathOptions={{ color: colors.go, weight: 1, opacity: 0.45, dashArray: '4 4', fillColor: colors.go, fillOpacity: 0.06 }} interactive={false} />
      ) : null}
      {studyInts.map((i) => (
        <Circle key={`r-${i.id}`} center={[i.lat, i.lon]} radius={radiusFt * FT_TO_M}
          pathOptions={{ color: colors.fg, weight: 1, opacity: 0.35, fillColor: colors.fg, fillOpacity: 0.07 }} interactive={false} />
      ))}
      {line?.length >= 2 ? (
        <Polyline positions={line} pathOptions={{ color: colors.go, weight: 6, opacity: mode === 'draw' ? 0.6 : 0.9, lineCap: 'round' }} interactive={false} />
      ) : null}
      {mode === 'draw' && line?.map((p, k) => (
        <Marker key={`v-${k}`} position={p} interactive={false}
          icon={L.divIcon({ className: 'ciq-vertex', iconSize: [10, 10], iconAnchor: [5, 5] })} />
      ))}
      {line?.length >= 1 ? (
        <Marker position={line[0]} icon={endIcon('A')} draggable={mode !== 'draw'}
          eventHandlers={{ dragend: (e) => onMoveEnd?.(0, [e.target.getLatLng().lat, e.target.getLatLng().lng]) }}>
          <Tooltip direction="left" offset={[-12, 0]}>Study start (A)</Tooltip>
        </Marker>
      ) : null}
      {line?.length >= 2 ? (
        <Marker position={line[line.length - 1]} icon={endIcon('B')} draggable={mode !== 'draw'}
          eventHandlers={{ dragend: (e) => onMoveEnd?.(line.length - 1, [e.target.getLatLng().lat, e.target.getLatLng().lng]) }}>
          <Tooltip direction="left" offset={[-12, 0]}>Study end (B)</Tooltip>
        </Marker>
      ) : null}
      {mode !== 'draw' && numbered.map((i) => (
        <Marker key={i.id} position={[i.lat, i.lon]} icon={pinIcon(i.n, { study: i.is_study, selected: i.id === selectedId })}
          eventHandlers={{ click: () => onSelect?.(i.id) }}>
          <Tooltip direction="top" offset={[0, -12]}>{i.name}</Tooltip>
        </Marker>
      ))}
    </MapContainer>
  )
}
