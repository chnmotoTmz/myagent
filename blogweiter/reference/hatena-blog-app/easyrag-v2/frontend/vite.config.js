import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    proxy: {
      '/files': {
        target: 'http://chanmoto.synology.me:22358',
        changeOrigin: true,
        headers: {
          'X-API-Key': 'key'
        }
      },
      '/file': {
        target: 'http://chanmoto.synology.me:22358',
        changeOrigin: true,
        headers: {
          'X-API-Key': 'key'
        }
      },
      '/image': {
        target: 'http://chanmoto.synology.me:22358',
        changeOrigin: true,
        headers: {
          'X-API-Key': 'key'
        }
      },
      '/generate': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
}) 