/**
 * Razorpay Standard Web Checkout Integration
 * Joybox Party Room
 */

import { getApiBaseUrl } from './apiBase';

const RAZORPAY_KEY_ID = import.meta?.env?.VITE_RAZORPAY_KEY_ID || '';

/**
 * Ensures Razorpay Checkout script is loaded on the page
 */
export function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (typeof window !== 'undefined' && window.Razorpay) {
      resolve(true);
      return;
    }
    const existing = document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]');
    if (existing) {
      existing.addEventListener('load', () => resolve(true));
      existing.addEventListener('error', () => resolve(false));
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

/**
 * Creates an order on the backend (POST /api/create-order)
 * @param {Object} params
 * @param {number} params.amount Amount in paise (minimum 100 paise = ₹1)
 * @param {string} [params.currency='INR'] Currency code
 * @param {string} [params.receipt] Unique receipt string
 * @param {Object} [params.notes] Metadata
 */
export async function createRazorpayOrder({ bookingReference, token, amount, currency = 'INR', receipt, notes = {} }) {
  const payload = bookingReference && token
    ? { bookingReference, token }
    : { bookingReference: receipt, token, amount, currency, notes };
  const res = await fetch(`${getApiBaseUrl()}/payments/create-order`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const json = await res.json().catch(() => ({}));
  if (!res.ok || json.success === false) {
    const errorMsg = json.error?.message || json.message || 'Failed to create payment order.';
    const err = new Error(errorMsg);
    err.status = res.status;
    err.code = json.error?.code;
    throw err;
  }

  // Handle both standard envelope format { data: { order_id, ... } } and flat { order_id, ... }
  const data = json.data || json;
  return {
    orderId: data.order_id || data.orderId || data.id,
    amount: data.amount,
    currency: data.currency || currency,
    keyId: data.key_id || data.keyId || RAZORPAY_KEY_ID,
  };
}

/**
 * Verifies payment signature on the backend (POST /api/verify-payment)
 * @param {Object} params
 * @param {string} params.orderId Razorpay order ID
 * @param {string} params.paymentId Razorpay payment ID
 * @param {string} params.signature Cryptographic HMAC-SHA256 signature
 * @param {string} [params.bookingReference] Optional booking ref
 * @param {string} [params.token] Optional booking token
 */
export async function verifyRazorpayPayment({ orderId, paymentId, signature, bookingReference, token }) {
  const res = await fetch(`${getApiBaseUrl()}/payments/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      razorpay_order_id: orderId,
      razorpay_payment_id: paymentId,
      razorpay_signature: signature,
      bookingReference,
      token,
    }),
  });

  const json = await res.json().catch(() => ({}));
  if (!res.ok || json.success === false) {
    const errorMsg = json.error?.message || json.message || 'Payment signature verification failed.';
    const err = new Error(errorMsg);
    err.status = res.status;
    err.code = json.error?.code;
    throw err;
  }

  return json.data || json;
}

/**
 * Opens Razorpay Standard Web Checkout Modal
 * @param {Object} options
 * @param {number} options.amount Amount in paise
 * @param {string} [options.currency='INR'] Currency code
 * @param {string} [options.name='Joybox Party Room'] Business name
 * @param {string} [options.description] Payment description
 * @param {Object} [options.prefill] Prefill customer data { name, contact, email }
 * @param {Object} [options.notes] Metadata
 * @param {string} [options.bookingReference] Optional booking ref for booking verification
 * @param {string} [options.bookingToken] Optional booking access token
 * @param {Function} options.onSuccess Callback on verified payment
 * @param {Function} [options.onFailure] Callback on payment error
 * @param {Function} [options.onDismiss] Callback on modal dismiss
 */
export async function openRazorpayCheckout({
  amount,
  currency = 'INR',
  name = 'Joybox Party Room',
  description = 'Celebration Reservation Advance Token',
  prefill = {},
  notes = {},
  bookingReference,
  bookingToken,
  onSuccess,
  onFailure,
  onDismiss,
}) {
  try {
    // 1. Ensure Razorpay checkout.js script is loaded
    const scriptLoaded = await loadRazorpayScript();
    if (!scriptLoaded || typeof window.Razorpay === 'undefined') {
      throw new Error('Razorpay SDK failed to load. Please check your internet connection.');
    }

    // 2. Create order on backend
    const order = await createRazorpayOrder({ bookingReference, token: bookingToken, amount, currency, notes });

    // 3. Configure Razorpay Standard Modal options
    const rzpOptions = {
      key: order.keyId || RAZORPAY_KEY_ID,
      amount: order.amount,
      currency: order.currency,
      name,
      description,
      order_id: order.orderId,
      prefill: {
        name: prefill.name || '',
        contact: prefill.contact || '',
        email: prefill.email || '',
      },
      theme: {
        color: '#1e0051', // Joybox primary purple
      },
      handler: async function (response) {
        try {
          // 4. Verify payment signature on backend
          const verifyResult = await verifyRazorpayPayment({
            orderId: response.razorpay_order_id,
            paymentId: response.razorpay_payment_id,
            signature: response.razorpay_signature,
            bookingReference,
            token: bookingToken,
          });

          if (onSuccess) {
            onSuccess({
              orderId: response.razorpay_order_id,
              paymentId: response.razorpay_payment_id,
              signature: response.razorpay_signature,
              verifyResult,
            });
          }
        } catch (verifyErr) {
          if (onFailure) {
            onFailure(verifyErr);
          }
        }
      },
      modal: {
        ondismiss: function () {
          if (onDismiss) {
            onDismiss();
          }
        },
      },
    };

    const rzpInstance = new window.Razorpay(rzpOptions);

    // 5. Handle payment failure events
    rzpInstance.on('payment.failed', function (response) {
      const err = new Error(response.error?.description || 'Payment transaction failed or cancelled by issuer.');
      err.details = response.error;
      if (onFailure) {
        onFailure(err);
      }
    });

    // 6. Open standard checkout modal
    rzpInstance.open();
    return rzpInstance;
  } catch (err) {
    if (onFailure) {
      onFailure(err);
    } else {
      throw err;
    }
  }
}

