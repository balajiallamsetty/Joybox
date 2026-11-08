import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import BookingsOpeningSoon from '../components/BookingsOpeningSoon';
import { api } from '../services/api';
import { BOOKINGS_OPEN } from '../services/config';

export default function PackagesPage() {
  const [packages, setPackages] = useState([]);
  const [addons, setAddons] = useState([]);
  const [activeOffer, setActiveOffer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSlowLoading, setIsSlowLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPackageForModal, setSelectedPackageForModal] = useState(null);

  const fetchCatalog = () => {
    setLoading(true);
    setError(null);
    setIsSlowLoading(false);
    Promise.all([
      api.getPackages(),
      api.getAddOns().catch(() => ({ items: [] })),
      api.getActiveOffers().catch(() => ({ offers: [] }))
    ])
      .then(([pkgData, addonData, offerData]) => {
        setPackages(pkgData?.items || []);
        setAddons(addonData?.items || []);
        if (offerData?.offers && offerData.offers.length > 0) {
          setActiveOffer(offerData.offers[0]);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "We couldn't load packages right now.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchCatalog();
  }, []);

  useEffect(() => {
    if (!loading) {
      setIsSlowLoading(false);
      return undefined;
    }
    const timer = setTimeout(() => {
      setIsSlowLoading(true);
    }, 5000);
    return () => clearTimeout(timer);
  }, [loading]);

  return (
    <div className="w-full min-h-screen bg-background">
      <Header />
      <main className="w-full pt-20 bg-background">
        <div className="flex flex-col w-full">
          {/* Top Festive Glow Under-Header */}
          <div className="w-full relative overflow-hidden bg-surface-container-low py-space-xl px-gutter">
            <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-[720px] h-72 bg-gradient-to-r from-secondary/15 via-tertiary-fixed/25 to-primary/10 blur-3xl pointer-events-none rounded-full"></div>
            <div className="max-w-7xl mx-auto flex flex-col items-center text-center relative z-10">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-surface-container-highest/80 backdrop-blur-md shadow-sm mb-4">
                <span className="w-2 h-2 rounded-full bg-secondary animate-ping"></span>
                <span className="font-label-sm text-label-sm tracking-widest text-primary uppercase">Transparent Pricing • No Hidden Fees</span>
              </div>
              <h1 className="font-display-hero text-display-hero text-primary max-w-4xl tracking-tight mb-4">
                Choose Your Joybox Celebration Package
              </h1>
              <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl leading-relaxed mb-6">
                Mama Edi Mana Adda — Vadlamudi, Guntur (Beside Durga Mart) | +91 78427 04429 • Flexible hourly booking with AC hall, sound system, customized decorations, and thrilling special effects entries.
              </p>
              {activeOffer && (
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary-fixed text-on-secondary-fixed text-sm font-bold shadow-sm mb-4">
                  <span className="material-symbols-outlined text-base">local_offer</span>
                  <span>Special Offer Active: {activeOffer.title || activeOffer.code} — Book today to claim!</span>
                </div>
              )}
            </div>
          </div>

          {/* Packages Comparison Grid */}
          <section className="w-full py-space-xl bg-background">
            <div className="max-w-7xl mx-auto px-gutter">
              {loading ? (
                <div className="flex flex-col items-center justify-center py-16 gap-4">
                  <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-secondary border-t-transparent"></div>
                  <p className="font-label-md text-label-md text-on-surface-variant animate-pulse">Loading party packages &amp; rates...</p>
                  {isSlowLoading && (
                    <p className="font-body-sm text-body-sm text-secondary max-w-md text-center animate-fadeIn">
                      Waking up the server, this can take up to a minute on first load.
                    </p>
                  )}
                </div>
              ) : error ? (
                <div className="max-w-xl mx-auto p-6 rounded-2xl bg-error-container text-on-error-container shadow-md text-center flex flex-col items-center gap-4">
                  <span className="material-symbols-outlined text-4xl text-error">error</span>
                  <div>
                    <h3 className="font-title-lg text-title-lg font-bold mb-1">We couldn't load packages right now.</h3>
                    <p className="font-body-sm text-body-sm opacity-90">{error}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={fetchCatalog}
                      className="px-6 py-2.5 rounded-full bg-secondary text-on-secondary font-label-md hover:bg-secondary-container transition-all shadow active:scale-95"
                    >
                      Retry
                    </button>
                    <a
                      href="https://wa.me/917842704429?text=Hi%20Joybox!%20I%20want%20to%20enquire%20about%20party%20packages%20in%20Vadlamudi."
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-5 py-2.5 rounded-full bg-[#075E54] text-on-primary font-label-md shadow hover:brightness-110"
                    >
                      WhatsApp Host
                    </a>
                  </div>
                </div>
              ) : packages.length === 0 ? (
                <div className="max-w-md mx-auto p-8 rounded-2xl bg-surface-container-low text-center flex flex-col items-center gap-3">
                  <span className="material-symbols-outlined text-4xl text-secondary">inventory_2</span>
                  <h3 className="font-title-lg text-title-lg text-primary font-bold">Bookings open soon</h3>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    Packages and availability are not configured yet. Booking stays closed until the host publishes them.
                  </p>
                  <a
                    href="https://wa.me/917842704429"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 px-6 py-2.5 rounded-full bg-secondary text-on-secondary font-label-md"
                  >
                    Contact on WhatsApp
                  </a>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg items-stretch">
                  {packages.map((pkg) => {
                    const isFeatured = pkg.isFeatured;
                    const priceRupees = pkg.pricePerHourMinor ? (pkg.pricePerHourMinor / 100).toLocaleString('en-IN') : '999';
                    return (
                      <div
                        key={pkg.code}
                        className={`relative rounded-lg p-space-lg shadow-xl flex flex-col justify-between transition-all ${
                          isFeatured
                            ? 'bg-surface-container-lowest -translate-y-2 ring-2 ring-secondary/20'
                            : pkg.code === 'diamond'
                            ? 'bg-primary-container text-on-primary'
                            : 'bg-surface-container-low'
                        }`}
                      >
                        {isFeatured && (
                          <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-5 py-1 rounded-full bg-tertiary-fixed text-on-tertiary-fixed font-label-sm text-label-sm uppercase tracking-widest shadow-md flex items-center gap-1">
                            <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                            <span>Most Popular Choice</span>
                          </div>
                        )}
                        <div>
                          <div className="flex justify-between items-start mb-space-sm mt-2">
                            <span className={`px-3.5 py-1 rounded-full font-label-sm text-label-sm uppercase ${
                              pkg.code === 'diamond' ? 'bg-tertiary text-on-tertiary' : 'bg-primary-fixed text-primary'
                            }`}>
                              {pkg.code === 'basic' ? 'Essential' : pkg.code === 'gold' ? 'Complete Party' : 'VIP Cinematic'}
                            </span>
                            <span className={`font-label-sm text-label-sm ${pkg.code === 'diamond' ? 'text-primary-fixed' : 'text-on-surface-variant'}`}>
                              Min. 1 Hour
                            </span>
                          </div>

                          <h3 className={`font-headline-md text-headline-md mb-1 ${pkg.code === 'diamond' ? 'text-on-primary' : 'text-primary'}`}>
                            {pkg.name} Tier
                          </h3>

                          <div className={`flex items-baseline gap-1 mb-space-md pb-space-sm p-3 rounded-DEFAULT ${
                            pkg.code === 'diamond' ? 'bg-primary/60' : 'bg-surface-container-lowest/60'
                          }`}>
                            <span className={`font-headline-lg text-headline-lg ${
                              pkg.code === 'diamond' ? 'text-tertiary-fixed' : isFeatured ? 'text-secondary' : 'text-primary'
                            }`}>
                              ₹{priceRupees}
                            </span>
                            <span className={`font-body-md text-body-md ${pkg.code === 'diamond' ? 'text-primary-fixed' : 'text-on-surface-variant'}`}>
                              / hour
                            </span>
                          </div>

                          <ul className={`flex flex-col gap-3 font-body-sm text-body-sm mb-space-lg ${
                            pkg.code === 'diamond' ? 'text-inverse-on-surface' : 'text-on-surface'
                          }`}>
                            {pkg.features && pkg.features.map((feat, i) => (
                              <li key={i} className="flex items-center gap-2">
                                <span className={`material-symbols-outlined text-base ${pkg.code === 'diamond' ? 'text-secondary-fixed' : 'text-secondary'}`}>check_circle</span>
                                <span>{feat}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        <Link
                          to={`/booking?package=${pkg.code}`}
                          onClick={(e) => {
                            if (!BOOKINGS_OPEN) {
                              e.preventDefault();
                              setSelectedPackageForModal(pkg.name);
                            }
                          }}
                          className={`w-full py-4 rounded-full font-label-md text-label-md text-center block transition-all shadow-md active:scale-95 ${
                            pkg.code === 'diamond'
                              ? 'bg-tertiary-fixed text-on-tertiary-fixed hover:bg-tertiary hover:text-on-tertiary'
                              : isFeatured
                              ? 'bg-secondary text-on-secondary hover:bg-secondary-container'
                              : 'bg-surface-container-high text-primary hover:bg-primary hover:text-on-primary'
                          }`}
                        >
                          Book {pkg.name} Package
                        </Link>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </section>

          {/* Add-ons Catalogue section */}
          <section className="w-full py-space-xl bg-surface-container-low">
            <div className="max-w-7xl mx-auto px-gutter">
              <div className="text-center max-w-2xl mx-auto mb-space-lg">
                <span className="font-label-sm text-label-sm text-secondary uppercase tracking-widest">A-La-Carte Party Boosters</span>
                <h3 className="font-headline-md text-headline-md text-primary">Enhance Your Celebration</h3>
                <p className="font-body-sm text-body-sm text-on-surface-variant">Customize with grand visual effects and celebration additions.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
                {addons.map((addon) => (
                  <div key={addon.code} className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm flex items-center justify-between">
                    <div className="flex items-center gap-space-sm">
                      <div className="w-12 h-12 rounded-full bg-primary-fixed flex items-center justify-center text-primary">
                        <span className="material-symbols-outlined text-2xl">{addon.iconSymbol || 'auto_awesome'}</span>
                      </div>
                      <div>
                        <h4 className="font-title-lg text-title-lg text-primary">{addon.name}</h4>
                        <p className="font-body-sm text-body-sm text-on-surface-variant">{addon.description}</p>
                      </div>
                    </div>
                    <span className="px-3 py-1 rounded-full bg-surface-container-high font-label-md text-label-md text-secondary font-bold">
                      +₹{addon.priceMinor ? addon.priceMinor / 100 : '300'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      </main>
      <BookingsOpeningSoon
        isOpen={Boolean(selectedPackageForModal)}
        onClose={() => setSelectedPackageForModal(null)}
        packageName={selectedPackageForModal || ''}
      />
      <Footer />
    </div>
  );
}

