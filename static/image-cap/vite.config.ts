import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  // ✅ 添加 envPrefix，确保 VITE_ 开头的环境变量暴露给客户端
  envPrefix: 'VITE_',
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        // ✅ 修复：删除 target 后面的空格
      },
      '/local-uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        // ✅ 修复：删除 target 后面的空格
      }
    }
  }
})
