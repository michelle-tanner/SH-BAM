import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forward /feedback and /subscribe to the FastAPI backend during dev.
      // This avoids CORS preflight entirely in the dev environment.
      '/feedback': 'http://localhost:8000',
      '/subscribe': 'http://localhost:8000',
    },
  },
})
