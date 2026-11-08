import { getApiBaseUrl } from './apiBase';

const TOKEN_KEY = 'joybox_admin_token';
let inMemoryToken = null;

export function setAdminSessionToken(token) {
  inMemoryToken = token;
  if (token) {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch (_e) {
      // Storage unavailable in restricted/incognito environments
    }
  } else {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch (_e) {
      // Storage unavailable in restricted/incognito environments
    }
  }
}

export function getAdminSessionToken() {
  if (inMemoryToken) return inMemoryToken;
  try {
    const stored = sessionStorage.getItem(TOKEN_KEY);
    if (stored) {
      inMemoryToken = stored;
      return stored;
    }
  } catch (_e) {
    // Storage unavailable in restricted/incognito environments
  }
  return null;
}

async function adminRequest(endpoint, options = {}) {
  const base = getApiBaseUrl();
  const url = `${base}/admin${endpoint}`;
  const token = getAdminSessionToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const config = {
    credentials: 'include', // essential for joybox_admin_session HttpOnly cookie
    ...options,
    headers,
  };

  try {
    const res = await fetch(url, config);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data?.error?.message || data?.message || `Request failed with status ${res.status}`);
      err.code = data?.error?.code || 'UNKNOWN_ERROR';
      err.details = data?.error?.details;
      err.status = res.status;
      throw err;
    }
    return data?.data !== undefined ? data.data : data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      const offlineErr = new Error('Cannot connect to Joybox server. Please ensure the backend is running.');
      offlineErr.code = 'NETWORK_ERROR';
      throw offlineErr;
    }
    throw err;
  }
}

export const adminApi = {
  // Authentication
  login: async (credentials) => {
    const data = await adminRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    if (data?.sessionToken) {
      setAdminSessionToken(data.sessionToken);
    }
    return data;
  },

  logout: async (csrfToken) => {
    try {
      return await adminRequest('/auth/logout', {
        method: 'POST',
        headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      });
    } finally {
      setAdminSessionToken(null);
    }
  },

  getMe: () =>
    adminRequest('/auth/me', {
      method: 'GET',
    }),

  changePassword: ({ currentPassword, newPassword, oldPassword }, csrfToken) => {
    const pwd = currentPassword || oldPassword;
    return adminRequest('/auth/change-password', {
      method: 'POST',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      body: JSON.stringify({
        oldPassword: pwd,
        currentPassword: pwd,
        newPassword,
      }),
    });
  },

  // Dashboard
  getDashboard: () =>
    adminRequest('/dashboard', {
      method: 'GET',
    }),

  // Bookings
  getBookings: (params = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.date) query.append('date', params.date);
    if (params.search) query.append('search', params.search);
    if (params.page) query.append('page', params.page);
    if (params.limit) query.append('limit', params.limit);
    const qs = query.toString();
    return adminRequest(`/bookings${qs ? `?${qs}` : ''}`, { method: 'GET' });
  },

  getBooking: (bookingRef) =>
    adminRequest(`/bookings/${bookingRef}`, {
      method: 'GET',
    }),

  updateBooking: (bookingRef, updateData, csrfToken) =>
    adminRequest(`/bookings/${bookingRef}`, {
      method: 'PATCH',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      body: JSON.stringify(updateData),
    }),

  createManualBooking: (bookingData, csrfToken) =>
    adminRequest('/bookings', {
      method: 'POST',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      body: JSON.stringify(bookingData),
    }),

  // Availability Blocks (emergency hall blocks / maintenance)
  getAvailabilityBlocks: () =>
    adminRequest('/availability-blocks', {
      method: 'GET',
    }),

  createAvailabilityBlock: (blockData, csrfToken) =>
    adminRequest('/availability-blocks', {
      method: 'POST',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      body: JSON.stringify(blockData),
    }),

  deleteAvailabilityBlock: (id, csrfToken) =>
    adminRequest(`/availability-blocks/${id}`, {
      method: 'DELETE',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
    }),

  // Catalog: Packages
  getPackages: () =>
    adminRequest('/packages', {
      method: 'GET',
    }),

  createPackage: (pkgData, csrfToken) =>
    adminRequest('/packages', {
      method: 'POST',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      body: JSON.stringify(pkgData),
    }),

  updatePackage: (id, pkgData, csrfToken) =>
    adminRequest(`/packages/${id}`, {
      method: 'PATCH',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      body: JSON.stringify(pkgData),
    }),

  // Catalog: Add-ons
  getAddOns: () =>
    adminRequest('/add-ons', {
      method: 'GET',
    }),

  createAddOn: (addOnData, csrfToken) =>
    adminRequest('/add-ons', {
      method: 'POST',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      body: JSON.stringify(addOnData),
    }),

  updateAddOn: (id, addOnData, csrfToken) =>
    adminRequest(`/add-ons/${id}`, {
      method: 'PATCH',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      body: JSON.stringify(addOnData),
    }),

  // Inquiries
  getInquiries: (params = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.page) query.append('page', params.page);
    if (params.limit) query.append('limit', params.limit);
    const qs = query.toString();
    return adminRequest(`/inquiries${qs ? `?${qs}` : ''}`, { method: 'GET' });
  },

  updateInquiry: (id, updateData, csrfToken) =>
    adminRequest(`/inquiries/${id}`, {
      method: 'PATCH',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      body: JSON.stringify(updateData),
    }),

  // Payments & Refunds
  getPayments: (params = {}) => {
    const query = new URLSearchParams();
    if (params.needsReview) query.append('needsReview', params.needsReview);
    if (params.search) query.append('search', params.search);
    if (params.page) query.append('page', params.page);
    if (params.limit) query.append('limit', params.limit);
    const qs = query.toString();
    return adminRequest(`/payments${qs ? `?${qs}` : ''}`, { method: 'GET' });
  },

  retryRefund: (paymentId, csrfToken) =>
    adminRequest(`/payments/${paymentId}/retry-refund`, {
      method: 'POST',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
    }),

  // Audit Logs
  getAuditLogs: (params = {}) => {
    const query = new URLSearchParams();
    if (params.limit) query.append('limit', params.limit);
    if (params.action) query.append('action', params.action);
    if (params.username) query.append('username', params.username);
    const qs = query.toString();
    return adminRequest(`/audit-logs${qs ? `?${qs}` : ''}`, { method: 'GET' });
  },
};

