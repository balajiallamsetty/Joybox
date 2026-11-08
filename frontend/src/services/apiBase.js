/**
 * Centralized API Base URL resolver for Joybox Party Room.
 * 
 * Normalizes VITE_API_BASE_URL:
 * - Trims whitespace and trailing slashes
 * - Guarantees a single '/api' suffix
 * - Restricts localhost fallback exclusively to development/test environments
 * - Emits a single actionable console error in misconfigured production builds
 */

export function getApiBaseUrl() {
  const raw = import.meta?.env?.VITE_API_BASE_URL;

  if (typeof raw === 'string' && raw.trim()) {
    const trimmed = raw.trim().replace(/\/+$/, '');
    return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`;
  }

  // Development & Vitest fallback only
  if (import.meta.env.DEV || import.meta.env.MODE === 'test') {
    return 'http://127.0.0.1:5000/api';
  }

  // Production misconfiguration: do NOT silently point to localhost
  console.error(
    '[Joybox Configuration Error] VITE_API_BASE_URL is missing in production. ' +
    'Please configure VITE_API_BASE_URL in your Vercel Project Settings (Environment Variables).'
  );
  return '';
}

export const API_BASE = getApiBaseUrl();
