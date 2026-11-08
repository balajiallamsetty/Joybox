import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useLanguage } from './LanguageContext';

export default function Header() {
  const { lang } = useLanguage();
  const location = useLocation();
  const waNumber = import.meta?.env?.VITE_WHATSAPP_NUMBER || '917842704429';
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const isTe = lang === 'te';
  const navLinks = [
    { path: '/', label: 'Home' },
    { path: '/packages', label: 'Packages & Add-ons' },
    { path: '/booking', label: 'Book Venue' },
    { path: '/gallery', label: 'Gallery & Themes' },
    { path: '/contact', label: 'Location & Contact' },
  ];

  return (
    <header className="fixed top-0 left-0 w-full z-50" data-testid="site-navbar">
      <div className="h-20 w-full px-3 sm:px-gutter bg-surface-container-lowest/85 backdrop-blur-xl shadow-[0_8px_24px_-4px_rgba(36,22,61,0.06),0_2px_6px_0_rgba(236,22,140,0.04)] flex items-center justify-between gap-2 transition-all duration-300">
        <div className="flex items-center gap-space-md">
          <Link to="/" className="flex items-center gap-space-sm group">
            <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center text-on-secondary shadow-[0_4px_14px_rgba(180,0,104,0.35)] transition-transform group-hover:scale-105">
              <span className="material-symbols-outlined text-[24px]">celebration</span>
            </div>
            <div className="flex flex-col">
              <span className="font-headline-sm text-headline-sm text-primary tracking-tight leading-none">Joybox</span>
              <span className="font-label-sm text-label-sm text-secondary leading-none">Party Room</span>
            </div>
          </Link>
          <div className="hidden xl:flex items-center gap-1 px-3 py-1 rounded-full bg-surface-container-low text-on-surface-variant font-label-sm text-label-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.8)]">
            <span className="material-symbols-outlined text-sm text-secondary">location_on</span>
            <span>Vadlamudi, Guntur (Beside Durga Mart)</span>
          </div>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden lg:flex items-center gap-2 p-1.5 rounded-full bg-surface-container/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.8)]">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`px-4 py-2 rounded-full transition-all font-label-md text-label-md ${
                  isActive
                    ? 'bg-surface-container-high text-primary font-bold shadow-[inset_0_1px_2px_rgba(255,255,255,0.8)]'
                    : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Action Controls */}
        <div className="flex items-center gap-space-sm">
          <a
            className="hidden md:flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-surface-container-low text-primary hover:bg-surface-container hover:text-primary transition-all font-label-sm text-label-sm shadow-[0_2px_8px_rgba(36,22,61,0.04)]"
            href="tel:+917842704429"
          >
            <span className="material-symbols-outlined text-base text-secondary">call</span>
            <span>+91 78427 04429</span>
          </a>

          <a
            className="hidden 2xl:flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-[#075E54] text-on-primary hover:opacity-95 transition-all font-label-sm text-label-sm shadow-[0_8px_20px_rgba(7,94,84,0.25)]"
            href={`https://wa.me/${waNumber}`}
            rel="noopener noreferrer"
            target="_blank"
          >
            <span className="material-symbols-outlined text-base">chat</span>
            <span>WhatsApp Us</span>
          </a>

          <Link
            className="flex items-center gap-1.5 px-4 sm:px-5 py-2 sm:py-2.5 rounded-full bg-secondary text-on-secondary visited:text-on-secondary hover:bg-[#d40074] transition-all font-label-md text-label-md shadow-[0_8px_20px_rgba(180,0,104,0.35)] active:scale-95"
            to="/booking"
          >
            <span className="material-symbols-outlined text-base text-on-secondary">confirmation_number</span>
            <span className="text-on-secondary">{isTe ? 'బుక్ చేయండి' : 'Book Now'}</span>
          </Link>

          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden flex items-center justify-center w-11 h-11 rounded-full bg-surface-container text-primary hover:bg-surface-container-high focus:outline-none focus:ring-2 focus:ring-primary transition-all shrink-0"
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={mobileMenuOpen}
            data-testid="mobile-menu-toggle"
          >
            <span className="material-symbols-outlined text-[24px]">
              {mobileMenuOpen ? 'close' : 'menu'}
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-x-0 top-20 bg-surface-container-lowest/95 backdrop-blur-2xl border-b border-outline shadow-2xl z-40 transition-all duration-300"
          data-testid="mobile-nav-drawer"
        >
          <nav className="flex flex-col p-4 gap-2">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center min-h-[44px] px-4 py-3 rounded-lg transition-all font-label-lg text-label-lg ${
                    isActive
                      ? 'bg-secondary text-on-secondary font-bold shadow-md'
                      : 'text-on-surface hover:bg-surface-container'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
            <div className="pt-2 border-t border-outline flex flex-col gap-2">
              <a
                href="tel:+917842704429"
                className="flex items-center gap-2 min-h-[44px] px-4 py-2.5 rounded-lg bg-surface-container-low text-primary font-label-md text-label-md"
              >
                <span className="material-symbols-outlined text-base text-secondary">call</span>
                <span>+91 78427 04429</span>
              </a>
              <a
                href={`https://wa.me/${waNumber}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 min-h-[44px] px-4 py-2.5 rounded-lg bg-[#075E54] text-on-primary font-label-md text-label-md"
              >
                <span className="material-symbols-outlined text-base">chat</span>
                <span>WhatsApp Us</span>
              </a>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}

