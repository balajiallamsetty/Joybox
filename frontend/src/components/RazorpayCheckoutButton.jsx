import React, { useState } from 'react';
import { openRazorpayCheckout } from '../services/razorpay';

export default function RazorpayCheckoutButton({
  amount = 10000, // 10000 paise default
  currency = 'INR',
  label = 'Pay via Razorpay (UPI / Card)',
  description = 'Joybox Party Room Reservation',
  prefill = {},
  notes = {},
  bookingReference,
  bookingToken,
  onSuccess,
  onError,
  className = '',
  disabled = false,
}) {
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleCheckout = async () => {
    if (disabled || loading) return;
    setLoading(true);
    setErrorMessage('');

    try {
      await openRazorpayCheckout({
        amount,
        currency,
        description,
        prefill,
        notes,
        bookingReference,
        bookingToken,
        onSuccess: (paymentData) => {
          setLoading(false);
          if (onSuccess) {
            onSuccess(paymentData);
          }
        },
        onFailure: (err) => {
          setLoading(false);
          setErrorMessage(err.message || 'Payment failed or was cancelled.');
          if (onError) {
            onError(err);
          }
        },
        onDismiss: () => {
          setLoading(false);
        },
      });
    } catch (err) {
      setLoading(false);
      setErrorMessage(err.message || 'Could not launch payment gateway.');
      if (onError) {
        onError(err);
      }
    }
  };

  const defaultStyles =
    'px-space-lg py-3 rounded-full bg-secondary text-on-secondary font-label-lg text-label-lg font-bold shadow-lg hover:bg-secondary-container transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed';

  return (
    <div className="flex flex-col gap-2 w-full sm:w-auto">
      {errorMessage && (
        <div className="p-3 rounded-lg bg-error-container text-on-error-container text-xs font-medium flex items-center gap-2 animate-fadeIn">
          <span className="material-symbols-outlined text-error text-[18px]">error</span>
          <span>{errorMessage}</span>
        </div>
      )}
      <button
        type="button"
        onClick={handleCheckout}
        disabled={disabled || loading}
        className={className || defaultStyles}
      >
        {loading ? (
          <>
            <div className="w-5 h-5 rounded-full border-2 border-on-secondary border-t-transparent animate-spin" />
            <span>Connecting to Razorpay...</span>
          </>
        ) : (
          <>
            <span className="material-symbols-outlined text-[20px]">account_balance_wallet</span>
            <span>{label}</span>
          </>
        )}
      </button>
    </div>
  );
}

