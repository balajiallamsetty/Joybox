import React from 'react';
import { Link } from 'react-router-dom';

export default function Footer() {
  const waNumber = import.meta?.env?.VITE_WHATSAPP_NUMBER || '917842704429';

  return (
    <footer className="w-full bg-surface-container-lowest border-t border-outline py-space-xl">
      <div className="max-w-7xl mx-auto px-gutter flex flex-col md:flex-row items-center justify-between gap-space-md">
        <div className="flex flex-col items-center md:items-start gap-1">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-on-secondary font-bold text-sm">
              <span className="material-symbols-outlined text-[18px]">celebration</span>
            </div>
            <span className="font-headline-sm text-headline-sm text-primary tracking-tight">Joybox Party Room</span>
          </div>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Beside Durga Mart, Vadlamudi, Guntur, Andhra Pradesh • “Mama Edi Mana Adda”
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-space-md font-label-md text-label-md text-on-surface-variant">
          <Link to="/" className="hover:text-primary transition-colors">Home</Link>
          <Link to="/packages" className="hover:text-primary transition-colors">Packages &amp; Add-ons</Link>
          <Link to="/booking" className="hover:text-primary transition-colors">Book Venue</Link>
          <Link to="/gallery" className="hover:text-primary transition-colors">Gallery</Link>
          <Link to="/contact" className="hover:text-primary transition-colors">Contact</Link>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={`https://wa.me/${waNumber}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#075E54] text-on-primary font-label-sm text-label-sm shadow-sm hover:brightness-110"
          >
            <span className="material-symbols-outlined text-sm">chat</span>
            <span>+91 78427 04429</span>
          </a>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-gutter mt-space-md pt-4 border-t border-outline flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-on-surface-variant">
        <div>
          © {new Date().getFullYear()} Joybox Party Room. Small Moments... Big Celebrations! All rights reserved.
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <Link to="/terms" className="hover:text-primary transition-colors">Terms of Service</Link>
          <Link to="/privacy" className="hover:text-primary transition-colors">Privacy Policy</Link>
          <Link to="/refund-policy" className="hover:text-primary transition-colors">Cancellation &amp; Refund Policy</Link>
        </div>
      </div>
    </footer>
  );
}

