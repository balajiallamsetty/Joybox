const API_BASE = import.meta?.env?.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const res = await fetch(url, config);
    const data = await res.json();
    if (!res.ok) {
      const err = new Error(data?.error?.message || data?.message || 'API request failed');
      err.code = data?.error?.code;
      err.details = data?.error?.details;
      err.status = res.status;
      throw err;
    }
    return data?.data !== undefined ? data.data : data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      const offlineErr = new Error('Cannot connect to Joybox server. Please ensure backend is running or contact us on WhatsApp.');
      offlineErr.code = 'NETWORK_ERROR';
      throw offlineErr;
    }
    throw err;
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

