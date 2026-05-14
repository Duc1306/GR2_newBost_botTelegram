import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import os from 'os'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // ── Windows EPERM rename fix ─────────────────────────────────────────
  // Root cause: Windows Defender / VS Code file-watcher holds an exclusive
  // lock on files inside the project tree, so Vite's atomic
  //   deps_temp_xxx  →  deps
  // rename fails with EPERM.
  // Fix: put the Vite cache in the OS temp directory (%TEMP%), which is
  // never watched by VS Code or scanned in real-time by Defender.
  cacheDir: path.join(os.tmpdir(), 'vite-newsbot'),

  optimizeDeps: {
    // Pre-bundle commonly used deps so the browser never triggers a
    // mid-session re-optimization (which would hit the same EPERM).
    include: [
      'react',
      'react-dom',
      'react/jsx-dev-runtime',
      'react-router-dom',
      'react-is',
      '@tanstack/react-query',
      '@mui/material',
      '@emotion/react',
      '@emotion/styled',
      'recharts',
      'd3-cloud',
    ],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    },
    watch: {
      // Do NOT watch node_modules or .git — reduces file-handle pressure
      // that contributes to EPERM on Windows.
      ignored: ['**/node_modules/**', '**/.git/**'],
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: process.env.NODE_ENV !== 'production',
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'mui-vendor': ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
          'query': ['@tanstack/react-query'],
          'charts': ['recharts', 'd3-cloud'],
        },
      },
    },
  }
})
