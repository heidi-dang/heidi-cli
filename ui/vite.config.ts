import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3002,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      '^/health': {
        target: 'http://127.0.0.1:7777',
        changeOrigin: true,
      },
      '^/agents': {
        target: 'http://127.0.0.1:7777',
        changeOrigin: true,
      },
      '^/run': {
        target: 'http://127.0.0.1:7777',
        changeOrigin: true,
      },
      '^/loop': {
        target: 'http://127.0.0.1:7777',
        changeOrigin: true,
      },
      '^/runs': {
        target: 'http://127.0.0.1:7777',
        changeOrigin: true,
      },
      '^/auth': {
        target: 'http://127.0.0.1:7777',
        changeOrigin: true,
      },
      '^/connect': {
        target: 'http://127.0.0.1:7777',
        changeOrigin: true,
      },
    },
  },
});