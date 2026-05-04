import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // Scan ALL source files at startup so Vite discovers every import
    // (including MUI icons) before the browser loads anything.
    // This prevents mid-session re-optimization that causes 504 cascades.
    entries: ['src/**/*.{js,jsx,ts,tsx}'],
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
    }
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
