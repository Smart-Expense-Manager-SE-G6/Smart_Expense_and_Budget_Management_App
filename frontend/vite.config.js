import process from 'node:process'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The browser only ever talks to Vite; /api is proxied to Django so the
// frontend and API share one origin (no CORS, session cookies just work).
const apiTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
    },
  },
})
