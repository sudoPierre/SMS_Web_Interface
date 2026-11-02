import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    allowedHosts: ['sms.pierre-qui-roule.fr'],
    port: 5173,
    // Same relative paths as the nginx proxy in production
    proxy: {
      '/api': 'http://localhost:8000',
      '/webhook': 'http://localhost:8000',
    },
  },
})
