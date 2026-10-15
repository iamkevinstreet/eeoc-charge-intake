import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development the API runs separately (uvicorn eeoc_intake.api:app); /api is proxied to it.
// In production the FastAPI service serves the built files from ui/dist at /.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: false },
});
