import React, { useEffect, useRef } from 'react';
import { VENUE_CONFIG } from '../services/config';

export default function BookingsOpeningSoon({ isOpen, onClose, packageName = 'celebration' }) {
  const dialogRef = useRef(null);
  const triggerRef = useRef(null);

  const cleanNumber = (VENUE_CONFIG?.whatsappNumber || '917842704429').replace(/\D/g, '') || '917842704429';
  const displayPackageName = packageName ? packageName.trim() : 'celebration';
  const waPrefill = encodeURIComponent(
    `Hi Joybox! I'd like to book a slot for the ${displayPackageName} package.`
  );
  const waUrl = `https://wa.me/${cleanNumber}?text=${waPrefill}`;

  useEffect(() => {
    if (!isOpen) return;

    triggerRef.current = document.activeElement;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // Focus the first focusable element inside the modal
    const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const focusableElements = dialogRef.current ? dialogRef.current.querySelectorAll(focusableSelector) : [];
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key === 'Tab' && dialogRef.current) {
        const nodes = dialogRef.current.querySelectorAll(focusableSelector);
        if (nodes.length === 0) return;

        const firstNode = nodes[0];
        const lastNode = nodes[nodes.length - 1];

        if (event.shiftKey) {
          if (document.activeElement === firstNode) {
            event.preventDefault();
            lastNode.focus();
          }
        } else {
          if (document.activeElement === lastNode) {
            event.preventDefault();
            firstNode.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      document.removeEventListener('keydown', handleKeyDown);
      if (triggerRef.current && typeof triggerRef.current.focus === 'function') {
        triggerRef.current.focus();
      }
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm transition-opacity animate-in fade-in"
      onClick={handleBackdropClick}
      data-testid="bookings-opening-soon-backdrop"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="bookings-opening-soon-title"
        aria-describedby="bookings-opening-soon-desc"
        data-testid="bookings-opening-soon-modal"
        className="w-full max-w-md bg-surface-container-lowest text-on-surface rounded-2xl p-6 sm:p-7 shadow-2xl border border-outline/20 flex flex-col gap-5 transition-all animate-in zoom-in-95"
      >
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-secondary/10 text-secondary flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-[28px]">celebration</span>
          </div>
          <div className="flex flex-col">
            <h2
              id="bookings-opening-soon-title"
              className="font-headline-sm text-headline-sm text-primary font-bold leading-tight"
            >
              Bookings Opening Soon
            </h2>
            <span className="font-label-sm text-label-sm text-secondary font-semibold mt-0.5">
              {displayPackageName} Package
            </span>
          </div>
        </div>

        <p
          id="bookings-opening-soon-desc"
          className="font-body-md text-body-md text-on-surface-variant leading-relaxed"
        >
          We&apos;re getting ready to welcome you! To reserve a slot, please contact us on WhatsApp.
        </p>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-3 pt-2 border-t border-outline/20">
          <button
            type="button"
            onClick={onClose}
            className="min-h-[44px] px-5 py-2.5 rounded-full bg-surface-container-high hover:bg-surface-container text-on-surface font-label-md text-label-md font-semibold transition-all active:scale-95 text-center"
            data-testid="bookings-opening-soon-close"
          >
            Close
          </button>
          <a
            href={waUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="min-h-[44px] px-6 py-2.5 rounded-full bg-[#075E54] hover:bg-[#064e46] text-white font-label-md text-label-md font-semibold shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 active:scale-95 text-center"
            data-testid="bookings-opening-soon-wa-btn"
          >
            <span className="material-symbols-outlined text-[20px]">chat</span>
            <span>Contact on WhatsApp</span>
          </a>
        </div>
      </div>
    </div>
  );
}
