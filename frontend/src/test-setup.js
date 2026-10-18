import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => cleanup())

// jsdom has no canvas or ResizeObserver; the Signal Flow sim and Leaflet only need stubs in tests.
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }
}
if (!window.matchMedia) {
  window.matchMedia = (q) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} })
}
HTMLCanvasElement.prototype.getContext = () => null
