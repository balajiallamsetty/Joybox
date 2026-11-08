import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiBase = env.VITE_API_BASE_URL;

  // F6: Production HTTPS Assertion - prevent mixed content in production builds
  if (mode === 'production' && apiBase) {
    if (apiBase.startsWith('http://') && !apiBase.includes('localhost') && !apiBase.includes('127.0.0.1')) {
      throw new Error(`[CRITICAL BUILD ERROR] VITE_API_BASE_URL must use https:// in production. Found: ${apiBase}`);
    }
  }

  return {
    plugins: [react()],
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.js'],
      include: ['src/**/*.{test,spec}.{js,jsx,ts,tsx}'],
      exclude: ['e2e/**', 'node_modules/**'],
    },
  };
});

