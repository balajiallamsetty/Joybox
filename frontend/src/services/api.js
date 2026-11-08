import { getApiBaseUrl } from './apiBase';

const REQUEST_TIMEOUT_MS = 60000;
const MAX_GET_RETRIES = 2;
const RETRY_BASE_DELAY_MS = 1000;

async function request(endpoint, options = {}) {
  const base = getApiBaseUrl();
  if (!base) {
    const configErr = new Error(
      'Joybox API is not configured. Please set VITE_API_BASE_URL in your deployment settings.'
    );
    configErr.code = 'CONFIG_ERROR';
    throw configErr;
  }

  const url = `${base}${endpoint}`;
  const method = (options.method || 'GET').toUpperCase();
  const maxRetries = method === 'GET' ? MAX_GET_RETRIES : 0;

  let attempt = 0;
  while (true) {
    const hasAbort = typeof globalThis.AbortController !== 'undefined';
    const controller = hasAbort ? new globalThis.AbortController() : null;
    const timeoutId = controller ? setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS) : null;

    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      signal: options.signal || (controller ? controller.signal : undefined),
    };

    try {
      const res = await fetch(url, config);
      if (timeoutId) clearTimeout(timeoutId);

      const data = await res.json().catch(() => null);
      if (!res.ok) {
        if (res.status >= 500 && method === 'GET' && attempt < maxRetries) {
          attempt++;
          await new Promise((r) => setTimeout(r, RETRY_BASE_DELAY_MS * attempt));
          continue;
        }
        const err = new Error(data?.error?.message || data?.message || `API request failed with status ${res.status}`);
        err.code = data?.error?.code || `HTTP_${res.status}`;
        err.details = data?.error?.details;
        err.status = res.status;
        throw err;
      }
      return data?.data !== undefined ? data.data : data;
    } catch (err) {
      if (timeoutId) clearTimeout(timeoutId);

      if (err.name === 'AbortError') {
        if (method === 'GET' && attempt < maxRetries) {
          attempt++;
          await new Promise((r) => setTimeout(r, RETRY_BASE_DELAY_MS * attempt));
          continue;
        }
        const timeoutErr = new Error('Server response timed out. The server may be warming up. Please try again.');
        timeoutErr.code = 'TIMEOUT_ERROR';
        throw timeoutErr;
      }

      if (err.name === 'TypeError' || (err.message && err.message.includes('fetch'))) {
        if (method === 'GET' && attempt < maxRetries) {
          attempt++;
          await new Promise((r) => setTimeout(r, RETRY_BASE_DELAY_MS * attempt));
          continue;
        }
        const offlineErr = new Error('Cannot connect to Joybox server. The server may be warming up or unreachable.');
        offlineErr.code = 'NETWORK_ERROR';
        throw offlineErr;
      }
      throw err;
    }
  }
}

export const api = {
  getHealth: () => request('/health'),
  getPublicConfig: () => request('/public-config'),
  getAvailability: (date, durationHours = 2, roomId = 'main') =>
    request(`/availability?date=${encodeURIComponent(date)}&durationHours=${encodeURIComponent(durationHours)}&roomId=${encodeURIComponent(roomId)}`),
  getPackages: () => request('/packages'),
  getPackage: (slug) => request(`/packages/${slug}`),
  getAddOns: () => request('/add-ons'),
  getActiveOffers: () => request('/offers/active'),
  getQuote: (quotePayload) => request('/bookings/quote', {
    method: 'POST',
    body: JSON.stringify(quotePayload),
  }),
  createInquiry: (inquiryPayload) => request('/inquiries', {
    method: 'POST',
    body: JSON.stringify(inquiryPayload),
  }),
  createOrder: (orderPayload) => request('/payments/create-order', {
    method: 'POST',
    body: JSON.stringify(orderPayload),
  }),
  verifyPayment: (verifyPayload) => request('/payments/verify', {
    method: 'POST',
    body: JSON.stringify(verifyPayload),
  }),
  getBooking: (reference, token = '') => request(`/bookings/${reference}${token ? `?token=${encodeURIComponent(token)}` : ''}`),
  cancelBooking: (reference, cancelPayload) => request(`/bookings/${reference}/cancel`, {
    method: 'POST',
    body: JSON.stringify(cancelPayload),
  }),
  getGallery: (category) => request(`/gallery${category && category !== 'all' ? `?category=${category}` : ''}`),
  getFaqs: (category) => request(`/faqs${category ? `?category=${category}` : ''}`),
};

