import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/ui/',
  server: {
    proxy: {
      '/game': 'http://localhost:8999',
      '/ai-game': 'http://localhost:8999',
      '/export': 'http://localhost:8999',
      '/deck': 'http://localhost:8999',
      '/health': 'http://localhost:8999',
    },
  },
  build: {
    outDir: 'dist',
  },
})
