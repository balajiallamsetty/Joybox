import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiBase = env.VITE_API_BASE_URL || process.env.VITE_API_BASE_URL;

  // Build-time guard: fail production builds on Vercel if VITE_API_BASE_URL is missing or points to localhost
  const isVercel = (process.env.VERCEL || env.VERCEL || '').trim() === '1';
  if (mode === 'production' && isVercel) {
    if (!apiBase || !apiBase.trim() || apiBase.includes('localhost') || apiBase.includes('127.0.0.1')) {
      throw new Error(
        `\n================================================================================\n` +
        `[VERCEL BUILD ERROR] Missing or invalid VITE_API_BASE_URL!\n` +
        `Found: "${apiBase || ''}"\n\n` +
        `To resolve:\n` +
        `1. Go to Vercel Dashboard -> Project Settings -> Environment Variables.\n` +
        `2. Add VITE_API_BASE_URL = https://your-backend-service.onrender.com/api\n` +
        `3. Save and trigger a fresh Redeploy (with "Use existing Build Cache" unchecked).\n` +
        `================================================================================\n`
      );
    }
  }

  // Production HTTPS Assertion - prevent mixed content in production builds
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

