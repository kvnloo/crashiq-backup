// Basemap: our own aitt-map v0.1.0 (California PMTiles, OSM + Protomaps), the one map all four apps share.
// Owner decision 2026-11-16: the light 'day' style on every map, whatever the app theme.
import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { Protocol } from 'pmtiles'
import { ATTRIBUTION, buildStyle, readTokens } from '@aitt/map'
import '../../node_modules/@aitt/map/src/theme/map-tokens.css' // readTokens() reads these; the package exports only "."

const TILES = 'https://tiles.aitransportationtools.com'
export const BASEMAP_URL = `${TILES}/basemap/v20261114.pmtiles`
export const GLYPHS = `${TILES}/fonts/{fontstack}/{range}.pbf`
export const TILE_ATTR = ATTRIBUTION
export const FT_TO_M = 0.3048

// maplibre-gl 6 loads its worker from a file beside its own module, which the Vite build doesn't copy: point it at
// the bundled asset (#363)
maplibregl.setWorkerUrl(workerUrl)
maplibregl.addProtocol('pmtiles', new Protocol().tile)

// The aitt-map day style. Its light sprite is served from public/sprites (copied from the package; the tile host has none).
export const basemapStyle = () => buildStyle(readTokens(), 'day',
  { basemapUrl: `pmtiles://${BASEMAP_URL}`, glyphs: GLYPHS, attribution: ATTRIBUTION })
