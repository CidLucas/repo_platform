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
      // The dev server runs inside the `blu_v3` Docker service (see
      // docker-compose.yml). From there `localhost` is the vite container
      // itself — NOT the host — so proxying to localhost:8003/8006 yields
      // ECONNREFUSED. Target the compose service names instead (all services
      // share the default network). Override via env for host-only dev.
      '/v1': {
        target: process.env.VITE_AGENT_API_PROXY_TARGET || 'http://agent_api:8000',
        changeOrigin: true,
      },
      '/api/tool-pool': {
        target: process.env.VITE_TOOL_POOL_PROXY_TARGET || 'http://tool_pool_api:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/tool-pool/, ''),
      },
    },
  },
})
