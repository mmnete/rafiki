import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // Allow external connections (needed for Docker)
    port: 5173,
    watch: {
      usePolling: true,  // Needed for hot reload in Docker
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    allowedHosts: [
      'rafiki-ai-web-e1a437f6a9aa.herokuapp.com',
      '.herokuapp.com'  // This allows any Heroku subdomain
    ]
  }
})