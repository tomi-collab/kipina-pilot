import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Concept API on oma palvelunsa hostin portissa 8082.
      '/api/concepts': {
        target: 'http://localhost:8082',
        changeOrigin: true,
      },
      // Devissä /api-kutsut menevät reveal-data-API:lle (host:lla 127.0.0.1:8081)
      '/api': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
    },
  },
})
