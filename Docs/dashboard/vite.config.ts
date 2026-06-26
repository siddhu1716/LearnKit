import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Multi-page app:
//   index.html -> landing page (home, opens on `npm run dev`)
//   app.html   -> React observability dashboard (sub-app, HashRouter)
//   docs.html  -> self-contained documentation page (opens in a new window)
export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 5173,
    open: '/index.html',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/healthz': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      input: {
        main: 'index.html',
        app: 'app.html',
        docs: 'docs.html',
      },
    },
  },
})
