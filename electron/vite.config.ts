import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// vite config for the react frontend
// we building something clean here fr

export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist/renderer',
    emptyOutDir: true
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    strictPort: true
  }
})

