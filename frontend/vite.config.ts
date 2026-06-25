import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const mcpTarget = env.VITE_MCP_URL || 'https://mcp-server-production-725c.up.railway.app'

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        '/api/mcp-health': {
          target: mcpTarget,
          changeOrigin: true,
          rewrite: () => '/',
        },
      },
    },
  }
})
