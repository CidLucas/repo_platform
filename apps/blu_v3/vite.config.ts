import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  envDir: resolve(__dirname, '../..'),
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@blu/auth': resolve(__dirname, '../../packages/blu-auth/src/index.ts'),
    },
  },
  server: {
    port: 5175,
    proxy: {
      '/api/tool-pool': {
        target: 'http://localhost:8006',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/tool-pool/, ''),
      },
    },
  },
})
