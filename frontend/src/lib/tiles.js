// Basemap: Esri Dark Gray Canvas (no API key; DemandIQ found CARTO's raster CDN now watermarks keyless tiles).
// Esri orders the path {z}/{y}/{x}, and has imagery only through z16, so Leaflet upscales past that.
export const TILE_URL = 'https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
export const TILE_MAX_NATIVE_ZOOM = 16
export const TILE_ATTR =
  'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
export const FT_TO_M = 0.3048
