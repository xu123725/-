import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  // 🔽 新增打包编译优化配置
  build: {
    // 调大单个代码块的大小警告限制到 2000kb，防止打包因为文件大而中断报错
    chunkSizeWarningLimit: 2000,
    rollupOptions: {
      output: {
        // 自动将 node_modules 中的第三方依赖（如 Element Plus）抽离到独立的 vendor 核心包中，大幅优化加载效率
        manualChunks(id) {
          if (id.includes('node_modules')) {
            return 'vendor';
          }
        }
      }
    }
  }
})