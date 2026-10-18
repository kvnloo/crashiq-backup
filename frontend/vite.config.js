import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: the app on :3000 calls /api/*, proxied to FastAPI on :8000 with /api stripped.
// Prod: FastAPI serves this build and strips /api itself, so the same URLs work.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.js'],
    css: false,
  },
})
