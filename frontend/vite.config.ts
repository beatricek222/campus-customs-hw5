import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The backend (http://localhost:8000) allows this page's origin, http://localhost:5173, through CORS.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, open: true },
})
