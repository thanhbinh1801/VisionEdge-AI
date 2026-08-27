import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      // Video demo & ảnh prototype được backend FastAPI mount tại cổng 8000
      '/videos': { target: 'http://localhost:8000', changeOrigin: true },
      // Clip 10s bằng chứng và ảnh crop mà backend trả về dưới dạng /media/...
      '/media': { target: 'http://localhost:8000', changeOrigin: true },
      '/api': { target: 'http://localhost:8000', changeOrigin: true, ws: true },
    },
  },
});
