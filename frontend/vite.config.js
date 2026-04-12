import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return

          if (id.includes('/marked/') || id.includes('/highlight.js/')) {
            return 'markdown'
          }

          if (
            id.includes('/vue-element-plus-x/') ||
            id.includes('/mermaid/') ||
            id.includes('/cytoscape/')
          ) {
            return 'ai-ui'
          }

          if (id.includes('/pdfmake/') || id.includes('/file-saver/')) {
            return 'export'
          }

          if (id.includes('/element-plus/')) {
            return 'element-plus'
          }
        }
      }
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
