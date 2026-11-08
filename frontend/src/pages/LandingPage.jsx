import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import BookingsOpeningSoon from '../components/BookingsOpeningSoon';
import { api } from '../services/api';
import { BOOKINGS_OPEN } from '../services/config';

export default function LandingPage() {
  const waNumber = import.meta?.env?.VITE_WHATSAPP_NUMBER || '917842704429';
  const [packages, setPackages] = useState([]);
  const [addons, setAddons] = useState([]);
  const [activeOffer, setActiveOffer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSlowLoading, setIsSlowLoading] = useState(false);
  const [catalogError, setCatalogError] = useState(null);
  const [calcTier, setCalcTier] = useState('basic');
  const [calcHours, setCalcHours] = useState(2);
  const [selectedAddons, setSelectedAddons] = useState([]);
  const [quote, setQuote] = useState(null);
  const [quoteError, setQuoteError] = useState('');
  const [selectedPackageForModal, setSelectedPackageForModal] = useState(null);

  // Fetch real catalog data on mount
  const fetchCatalog = () => {
    setLoading(true);
    setCatalogError(null);
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
        setCatalogError(err.message || "We couldn't load packages right now.");
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

  // Update live quote whenever estimator params change
  useEffect(() => {
    if (!packages.length) return undefined;
    api.getQuote({
      packageCode: calcTier,
      durationHours: Number(calcHours),
      addOnCodes: selectedAddons,
      applyPromo: true,
    })
      .then((data) => {
        setQuote(data);
        setQuoteError('');
      })
      .catch((err) => {
        setQuoteError(err.message);
      });
  }, [packages.length, calcTier, calcHours, selectedAddons]);

  const toggleAddon = (code) => {
    setSelectedAddons((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const basicPkg = packages.find((p) => p.code === 'basic');
  const goldPkg = packages.find((p) => p.code === 'gold');
  const diamondPkg = packages.find((p) => p.code === 'diamond');

  const _bookingsOpen = !loading && packages.length > 0;
  const basicPrice = basicPkg?.pricePerHourMinor ? `₹${(basicPkg.pricePerHourMinor / 100).toLocaleString('en-IN')}` : '';
  const goldPrice = goldPkg?.pricePerHourMinor ? `₹${(goldPkg.pricePerHourMinor / 100).toLocaleString('en-IN')}` : '';
  const diamondPrice = diamondPkg?.pricePerHourMinor ? `₹${(diamondPkg.pricePerHourMinor / 100).toLocaleString('en-IN')}` : '';
  const promoPrice = activeOffer?.promoPricePerHourMinor ? `₹${(activeOffer.promoPricePerHourMinor / 100).toLocaleString('en-IN')}` : '';

  const bubbleAddon = addons.find((a) => a.code === 'bubble_entry');
  const fogAddon = addons.find((a) => a.code === 'fog_entry');
  const sparkAddon = addons.find((a) => a.code === 'cold_fire_one_shot');

  const bubblePrice = bubbleAddon?.priceMinor ? `₹${(bubbleAddon.priceMinor / 100).toLocaleString('en-IN')}` : '';
  const fogPrice = fogAddon?.priceMinor ? `₹${(fogAddon.priceMinor / 100).toLocaleString('en-IN')}` : '';
  const sparkPrice = sparkAddon?.priceMinor ? `₹${(sparkAddon.priceMinor / 100).toLocaleString('en-IN')}` : '';

  return (
    <div className="w-full min-h-screen bg-background">
      <Header />
      <main className="w-full pt-20 bg-background">
        <div className="flex flex-col w-full">
          {/* HERO SECTION WITH VERBATIM TAILWIND FROM STITCH EXPORT */}
          <section className="relative w-full overflow-hidden bg-gradient-to-b from-primary-container via-primary to-surface-container-low text-on-primary -mt-20 pt-20 pb-space-xl">
            <div className="absolute -top-12 -left-20 w-96 h-96 rounded-full bg-secondary opacity-30 blur-3xl pointer-events-none"></div>
            <div className="absolute top-1/4 -right-16 w-80 h-80 rounded-full bg-tertiary-container opacity-25 blur-3xl pointer-events-none"></div>
            <div className="absolute bottom-10 left-1/3 w-72 h-72 rounded-full bg-secondary-container opacity-20 blur-2xl pointer-events-none"></div>
            <svg aria-hidden="true" className="absolute inset-0 w-full h-full pointer-events-none opacity-30">
              <circle className="animate-pulse" cx="12%" cy="25%" fill="#FFD72F" r="14"></circle>
              <circle cx="88%" cy="18%" fill="#EC168C" r="18"></circle>
              <rect fill="#FFE175" height="12" rx="3" transform="rotate(25 22 45)" width="12" x="22%" y="45%"></rect>
              <rect fill="#E10084" height="14" rx="4" transform="rotate(45 78 60)" width="14" x="78%" y="60%"></rect>
            </svg>
            <div className="relative max-w-7xl mx-auto px-gutter">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-center pt-space-md">
                <div className="lg:col-span-7 flex flex-col text-left">
                  <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-surface-container-lowest/15 backdrop-blur-md shadow-md text-tertiary-fixed mb-space-sm w-fit">
                    <span className="material-symbols-outlined text-base animate-bounce" style={{ fontVariationSettings: "'FILL' 1" }}>celebration</span>
                    <span className="font-label-sm text-label-sm uppercase tracking-wider font-bold">MAMA EDI MANA ADDA • VADLAMUDI, GUNTUR</span>
                  </div>
                  <h1 className="font-display-hero text-display-hero max-w-3xl tracking-tight leading-tight mb-space-sm">
                    Small Moments... <br />
                    <span className="text-tertiary-fixed">Big Celebrations!</span>
                  </h1>
                  <p className="font-body-lg text-body-lg text-primary-fixed max-w-xl mb-space-md leading-relaxed">
                    Your neighborhood private AC celebration haven beside Durga Mart, Vadlamudi. Exclusively crafted for surprise birthdays, heartfelt anniversaries, reunion bashes, movie screenings, and intimate family milestones.
                  </p>
                  <div className="flex flex-wrap items-center gap-space-sm mb-space-md">
                    <a className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-secondary text-on-secondary font-label-lg text-label-lg shadow-xl hover:bg-secondary-container transition-all hover:scale-105 active:scale-95" href="#booking-calculator">
                      <span className="material-symbols-outlined text-xl">calendar_month</span>
                      <span>Check Live Availability &amp; Slots</span>
                    </a>
                    <a className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-[#075E54] text-on-primary font-label-lg text-label-lg shadow-lg hover:brightness-110 transition-all hover:scale-105 active:scale-95" href={`https://wa.me/${waNumber}?text=Hi%20Joybox!%20I%20want%20to%20enquire%20about%20booking%20a%20private%20party%20slot%20in%20Vadlamudi.`} rel="noopener noreferrer" target="_blank">
                      <span className="material-symbols-outlined text-xl">chat</span>
                      <span>Instant WhatsApp (+91 78427 04429)</span>
                    </a>
                    <a className="flex items-center gap-2 px-5 py-3.5 rounded-full bg-surface-container-lowest text-primary font-label-md text-label-md shadow-md hover:bg-surface-container transition-all" href="tel:+917842704429">
                      <span className="material-symbols-outlined text-lg text-tertiary">call</span>
                      <span>Call Host Kiran Kumar</span>
                    </a>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-primary-fixed font-body-sm text-body-sm mb-space-md py-2 px-3 rounded-xl bg-primary">
                    <span className="flex items-center gap-1"><span className="material-symbols-outlined text-tertiary-fixed text-sm">ac_unit</span>100% Private AC Hall</span>
                    <span className="flex items-center gap-1"><span className="material-symbols-outlined text-tertiary-fixed text-sm">check_circle</span>No Hidden Cleaning Fees</span>
                    <span className="flex items-center gap-1"><span className="material-symbols-outlined text-tertiary-fixed text-sm">lock_clock</span>Zero Overlapping Bookings</span>
                    <span className="flex items-center gap-1"><span className="material-symbols-outlined text-tertiary-fixed text-sm">restaurant</span>Outside Food &amp; Catering Allowed</span>
                  </div>

                  {activeOffer && basicPkg && (
                  <div className="rounded-lg bg-primary p-3.5 border border-primary-fixed/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-tertiary-fixed flex items-center justify-center text-on-tertiary-fixed">
                        <span className="material-symbols-outlined text-xl" style={{ fontVariationSettings: "'FILL' 1" }}>local_fire_department</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded-full bg-secondary text-on-secondary font-label-sm text-label-sm uppercase font-bold text-xs">{activeOffer.name}</span>
                        </div>
                        <p className="font-label-md text-label-md text-on-primary mt-0.5">{activeOffer.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-tertiary-fixed text-xs font-bold text-on-tertiary-fixed">
                      <span className="w-2 h-2 rounded-full bg-secondary animate-ping"></span>
                      <span>{activeOffer.slotsRemainingThisMonth} slots remaining this month</span>
                    </div>
                  </div>
                  )}
                </div>

                {/* Hero Right Visual */}
                <div className="lg:col-span-5 relative flex flex-col items-center">
                  <div className="relative w-full max-w-md aspect-[4/5] rounded-lg overflow-hidden shadow-2xl bg-surface-container-high ring-2 ring-surface-container-lowest/30">
                    <img className="w-full h-full object-cover" alt="Joyful celebration party hall at Joybox Vadlamudi with glowing neon backdrop and balloon arch." src="/images/placeholders/hero-hall-neon.jpg" />
                    <div className="absolute inset-x-0 bottom-0 bg-primary flex flex-col justify-end p-space-md">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="px-2 py-0.5 rounded-full bg-secondary text-on-secondary font-label-sm text-label-sm font-bold text-xs">Vadlamudi Adda</span>
                        <span className="text-xs text-primary-fixed font-semibold">• Beside Durga Mart</span>
                      </div>
                      <p className="font-headline-sm text-headline-sm text-on-primary leading-tight">Where Celebrations Feel Special &amp; Exclusive</p>
                    </div>
                  </div>
                  <div className="absolute -bottom-4 right-6 px-4 py-2 rounded-lg bg-tertiary-fixed text-on-tertiary-fixed shadow-xl flex items-center gap-2">
                    <span className="material-symbols-outlined text-xl" style={{ fontVariationSettings: "'FILL' 1" }}>stars</span>
                    <span className="font-label-sm text-label-sm font-bold">Vadlamudi's #1 Party Adda</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {activeOffer && basicPkg && (
          <section className="max-w-7xl w-full mx-auto px-gutter -mt-8 relative z-20">
            <div className="w-full rounded-lg bg-surface-container-lowest p-space-lg shadow-xl flex flex-col lg:flex-row items-center justify-between gap-space-md">
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-space-md">
                <div className="w-16 h-16 rounded-full bg-tertiary-container/30 flex items-center justify-center text-tertiary shadow-inner">
                  <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>local_fire_department</span>
                </div>
                <div className="flex flex-col">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="px-3 py-1 rounded-full bg-secondary text-on-secondary font-label-sm text-label-sm uppercase tracking-wider">{activeOffer.name}</span>
                  </div>
                  <h2 className="font-headline-md text-headline-md text-primary">
                    {activeOffer.description}
                  </h2>
                  <p className="font-body-sm text-body-sm text-on-surface-variant flex items-center gap-1.5 mt-0.5">
                    <span className="material-symbols-outlined text-secondary text-sm">check_circle</span>
                    <span>Server-authoritative availability locks slot instantly. Resets every calendar month.</span>
                  </p>
                </div>
              </div>
              <div className="flex flex-col sm:flex-row items-center gap-space-sm w-full lg:w-auto">
                <div className="p-3 rounded-full bg-surface-container-high flex items-center gap-2 px-4 shadow-inner">
                  <span className="w-3 h-3 rounded-full bg-secondary animate-ping"></span>
                  <span className="font-label-sm text-label-sm text-on-surface font-bold">{activeOffer.slotsRemainingThisMonth} slots remaining this month</span>
                </div>
                <a className="w-full sm:w-auto text-center px-6 py-3 rounded-full bg-secondary text-on-secondary font-label-md text-label-md hover:bg-secondary-container shadow-md transition-all active:scale-95 whitespace-nowrap" href="#booking-calculator">
                  View this offer
                </a>
              </div>
            </div>
          </section>
          )}

          {/* 3 PACKAGES SNAPSHOT SECTION */}
          <section className="w-full py-space-xl bg-background" id="packages-section">
            <div className="max-w-7xl mx-auto px-gutter">
              <div className="flex flex-col md:flex-row md:items-end justify-between mb-space-lg gap-4">
                <div>
                  <div className="flex items-center gap-2 text-secondary font-label-sm text-label-sm uppercase tracking-widest mb-1">
                    <span className="material-symbols-outlined text-base">style</span>
                    <span>Tailored Celebration Packages</span>
                  </div>
                  <h2 className="font-headline-lg text-headline-lg text-primary tracking-tight">
                    Transparent Hourly Pricing, Zero Hidden Fees
                  </h2>
                </div>
                <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
                  Pick your ideal tier. Every booking guarantees entire private hall access for you and your guests.
                </p>
              </div>

              {loading ? (
                <div className="rounded-2xl border border-outline/30 bg-surface-container-low p-12 text-center flex flex-col items-center justify-center gap-4">
                  <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-secondary border-t-transparent"></div>
                  <p className="font-label-md text-label-md text-on-surface-variant animate-pulse">Loading celebration packages &amp; rates...</p>
                  {isSlowLoading && (
                    <p className="font-body-sm text-body-sm text-secondary max-w-md animate-fadeIn">
                      Waking up the server, this can take up to a minute on first load.
                    </p>
                  )}
                </div>
              ) : catalogError ? (
                <div className="rounded-2xl border border-error/20 bg-error-container text-on-error-container p-8 text-center flex flex-col items-center justify-center gap-4 shadow-md max-w-xl mx-auto">
                  <span className="material-symbols-outlined text-4xl text-error">error</span>
                  <div>
                    <h3 className="font-headline-md text-headline-md font-bold mb-1">We couldn't load packages right now.</h3>
                    <p className="font-body-sm text-body-sm opacity-90">{catalogError}</p>
                  </div>
                  <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
                    <button
                      type="button"
                      onClick={fetchCatalog}
                      className="px-6 py-2.5 rounded-full bg-secondary text-on-secondary font-label-md hover:bg-secondary-container transition-all shadow active:scale-95"
                    >
                      Retry
                    </button>
                    <a
                      href={`https://wa.me/${waNumber}?text=${encodeURIComponent('Hi Joybox! I had trouble loading party packages on the website and would like details.')}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-5 py-2.5 rounded-full bg-[#075E54] text-on-primary font-label-md shadow hover:brightness-110 flex items-center gap-1.5"
                    >
                      <span className="material-symbols-outlined text-base">chat</span>
                      <span>Contact on WhatsApp</span>
                    </a>
                  </div>
                </div>
              ) : packages.length === 0 ? (
                <div className="rounded-lg border border-outline bg-surface-container-low p-8 text-center">
                  <h3 className="font-headline-md text-headline-md text-primary">Bookings open soon</h3>
                  <p className="font-body-md text-body-md text-on-surface-variant mt-2">
                    Packages and availability are not configured yet. Booking stays closed until the host publishes them.
                  </p>
                </div>
              ) : (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg items-stretch">
                {/* 1. BASIC PACKAGE */}
                <div className="rounded-lg bg-surface-container-low p-space-lg shadow-md flex flex-col justify-between transition-all hover:shadow-xl hover:-translate-y-1">
                  <div>
                    <div className="flex justify-between items-start mb-space-sm">
                      <span className="px-3.5 py-1 rounded-full bg-primary-fixed text-primary font-label-sm text-label-sm uppercase">Essential</span>
                      <span className="font-label-sm text-label-sm text-on-surface-variant">Min. 1 Hour</span>
                    </div>
                    <h3 className="font-headline-md text-headline-md text-primary mb-1">Basic Tier</h3>
                    <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-md">Perfect for intimate cake cutting, short surprise milestones, and quick family moments.</p>
                    <div className="flex items-baseline gap-1 mb-space-md pb-space-sm bg-surface-container-lowest/60 p-3 rounded-DEFAULT">
                      <span className="font-headline-lg text-headline-lg text-primary">{basicPrice}</span>
                      <span className="font-body-md text-body-md text-on-surface-variant">/ hour</span>
                      {promoPrice && <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-bold">Offer {promoPrice}/hr</span>}
                    </div>
                    <ul className="flex flex-col gap-3 font-body-sm text-body-sm text-on-surface mb-space-lg">
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-secondary text-base">check_circle</span><span>Entire Air-Conditioned Private Hall</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-secondary text-base">check_circle</span><span>Curated Birthday / Occasion Theme Decor</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-secondary text-base">check_circle</span><span>High-output Sound System &amp; Party Music</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-secondary text-base">check_circle</span><span>Vibrant Ambient Hall Lighting</span></li>
                      <li className="flex items-center gap-2 text-on-surface-variant line-through"><span className="material-symbols-outlined text-base">cancel</span><span>Fresh Birthday Cake Included</span></li>
                      <li className="flex items-center gap-2 text-on-surface-variant line-through"><span className="material-symbols-outlined text-base">cancel</span><span>Custom Neon Name Letters</span></li>
                    </ul>
                  </div>
                  <Link
                    to="/booking?package=basic"
                    onClick={(e) => {
                      if (!BOOKINGS_OPEN) {
                        e.preventDefault();
                        setSelectedPackageForModal('Basic');
                      }
                    }}
                    className="w-full py-3.5 rounded-full bg-surface-container-high text-primary hover:bg-primary hover:text-on-primary font-label-md text-label-md text-center transition-all shadow-sm block"
                  >
                    Select Basic ({basicPrice}/hr)
                  </Link>
                </div>

                {/* 2. GOLD PACKAGE (MOST POPULAR) */}
                <div className="relative rounded-lg bg-surface-container-lowest p-space-lg shadow-xl flex flex-col justify-between -translate-y-2 transition-all hover:shadow-2xl">
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-5 py-1 rounded-full bg-tertiary-fixed text-on-tertiary-fixed font-label-sm text-label-sm uppercase tracking-widest shadow-md flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                    <span>Most Popular Choice</span>
                  </div>
                  <div>
                    <div className="flex justify-between items-start mb-space-sm mt-2">
                      <span className="px-3.5 py-1 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm uppercase">Complete Party</span>
                      <span className="font-label-sm text-label-sm text-secondary font-semibold">Bestseller</span>
                    </div>
                    <h3 className="font-headline-md text-headline-md text-primary mb-1">Gold Tier</h3>
                    <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-md">The complete hassle-free party package. Cake, personalized display &amp; decor all ready.</p>
                    <div className="flex items-baseline gap-1 mb-space-md pb-space-sm bg-surface-container-low p-3 rounded-DEFAULT">
                      <span className="font-headline-lg text-headline-lg text-secondary">{goldPrice}</span>
                      <span className="font-body-md text-body-md text-on-surface-variant">/ hour</span>
                      <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed font-bold">Includes 0.5kg Cake</span>
                    </div>
                    <ul className="flex flex-col gap-3 font-body-sm text-body-sm text-on-surface mb-space-lg">
                      <li className="flex items-center gap-2 font-semibold text-primary"><span className="material-symbols-outlined text-secondary text-base">done_all</span><span>Everything in Basic Package</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-secondary text-base">cake</span><span>Fresh 0.5 kg Birthday / Celebration Cake</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-secondary text-base">check_circle</span><span>Personalized Acrylic / Neon Name Display</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-secondary text-base">check_circle</span><span>Easel Stand Custom Welcome Chalkboard</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-secondary text-base">check_circle</span><span>Dedicated Table for Guest Treats &amp; Gifts</span></li>
                      <li className="flex items-center gap-2 text-on-surface-variant line-through"><span className="material-symbols-outlined text-base">cancel</span><span>Bubble &amp; Fog Special Effects</span></li>
                    </ul>
                  </div>
                  <Link
                    to="/booking?package=gold"
                    onClick={(e) => {
                      if (!BOOKINGS_OPEN) {
                        e.preventDefault();
                        setSelectedPackageForModal('Gold');
                      }
                    }}
                    className="w-full py-4 rounded-full bg-secondary text-on-secondary hover:bg-secondary-container font-label-md text-label-md text-center transition-all shadow-lg active:scale-95 block"
                  >
                    Book Gold Package ({goldPrice}/hr)
                  </Link>
                </div>

                {/* 3. DIAMOND PACKAGE */}
                <div className="rounded-lg bg-primary-container text-on-primary p-space-lg shadow-lg flex flex-col justify-between transition-all hover:shadow-xl hover:-translate-y-1">
                  <div>
                    <div className="flex justify-between items-start mb-space-sm">
                      <span className="px-3.5 py-1 rounded-full bg-tertiary text-on-tertiary font-label-sm text-label-sm uppercase">VIP Cinematic</span>
                      <span className="font-label-sm text-label-sm text-primary-fixed">Milestone Special</span>
                    </div>
                    <h3 className="font-headline-md text-headline-md text-on-primary mb-1">Diamond Tier</h3>
                    <p className="font-body-sm text-body-sm text-primary-fixed mb-space-md">Spectacular grand entries with cinematic effects, cold spark shots, and fairytale bubbles.</p>
                    <div className="flex items-baseline gap-1 mb-space-md pb-space-sm bg-primary/60 p-3 rounded-DEFAULT">
                      <span className="font-headline-lg text-headline-lg text-tertiary-fixed">{diamondPrice}</span>
                      <span className="font-body-md text-body-md text-primary-fixed">/ hour</span>
                      <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-surface-container-lowest text-primary font-bold">Cinematic FX</span>
                    </div>
                    <ul className="flex flex-col gap-3 font-body-sm text-body-sm text-inverse-on-surface mb-space-lg">
                      <li className="flex items-center gap-2 font-semibold text-tertiary-fixed"><span className="material-symbols-outlined text-base">done_all</span><span>Everything in Gold Package</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-tertiary-fixed text-base">bubble_chart</span><span>Magical High-Density Bubble Machine Entry</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-tertiary-fixed text-base">cloud</span><span>Cinematic Low-Lying Fog Cloud Entry</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-tertiary-fixed text-base">flare</span><span>1 Indoor Cold-Fire Spark Gun Blast</span></li>
                      <li className="flex items-center gap-2"><span className="material-symbols-outlined text-tertiary-fixed text-base">photo_camera</span><span>Assisted Lighting for 4K Video Captures</span></li>
                    </ul>
                  </div>
                  <Link
                    to="/booking?package=diamond"
                    onClick={(e) => {
                      if (!BOOKINGS_OPEN) {
                        e.preventDefault();
                        setSelectedPackageForModal('Diamond');
                      }
                    }}
                    className="w-full py-3.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed hover:bg-tertiary hover:text-on-tertiary font-label-md text-label-md text-center transition-all shadow-md block"
                  >
                    Book Diamond Package ({diamondPrice}/hr)
                  </Link>
                </div>
              </div>
              )}
            </div>
          </section>

          {/* ADD-ON HIGHLIGHTS GRID */}
          <section className="w-full py-space-lg bg-surface-container-low">
            <div className="max-w-7xl mx-auto px-gutter">
              <div className="text-center max-w-2xl mx-auto mb-space-lg">
                <span className="font-label-sm text-label-sm text-secondary uppercase tracking-widest">Custom Sparkle</span>
                <h3 className="font-headline-md text-headline-md text-primary">A-La-Carte Party Boosters</h3>
                <p className="font-body-sm text-body-sm text-on-surface-variant">Add magical grand elements to any package to personalize your celebration moment.</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
                <div className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm flex items-center justify-between">
                  <div className="flex items-center gap-space-sm">
                    <div className="w-12 h-12 rounded-full bg-primary-fixed flex items-center justify-center text-primary">
                      <span className="material-symbols-outlined text-2xl">bubble_chart</span>
                    </div>
                    <div>
                      <h4 className="font-title-lg text-title-lg text-primary">Bubble Machine Entry</h4>
                      <p className="font-body-sm text-body-sm text-on-surface-variant">Magical floating bubbles for cake entry</p>
                    </div>
                  </div>
                  {bubblePrice && <span className="px-3 py-1 rounded-full bg-surface-container-high font-label-md text-label-md text-secondary font-bold">+{bubblePrice}</span>}
                </div>
                <div className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm flex items-center justify-between">
                  <div className="flex items-center gap-space-sm">
                    <div className="w-12 h-12 rounded-full bg-secondary-fixed flex items-center justify-center text-secondary">
                      <span className="material-symbols-outlined text-2xl">cloud</span>
                    </div>
                    <div>
                      <h4 className="font-title-lg text-title-lg text-primary">Low-Lying Fog Cloud</h4>
                      <p className="font-body-sm text-body-sm text-on-surface-variant">Dense floor mist for royal entry vibes</p>
                    </div>
                  </div>
                  {fogPrice && <span className="px-3 py-1 rounded-full bg-surface-container-high font-label-md text-label-md text-secondary font-bold">+{fogPrice}</span>}
                </div>
                <div className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm flex items-center justify-between">
                  <div className="flex items-center gap-space-sm">
                    <div className="w-12 h-12 rounded-full bg-tertiary-fixed flex items-center justify-center text-tertiary">
                      <span className="material-symbols-outlined text-2xl">flare</span>
                    </div>
                    <div>
                      <h4 className="font-title-lg text-title-lg text-primary">Cold-Fire Spark Gun</h4>
                      <p className="font-body-sm text-body-sm text-on-surface-variant">Safe indoor pyrotechnic spark blast</p>
                    </div>
                  </div>
                  {sparkPrice && <span className="px-3 py-1 rounded-full bg-surface-container-high font-label-md text-label-md text-secondary font-bold">+{sparkPrice} / shot</span>}
                </div>
              </div>
            </div>
          </section>

          {/* INTERACTIVE PRICE ESTIMATOR CALCULATOR (WIRED TO POST /api/bookings/quote) */}
          <section className="w-full py-space-xl bg-background" id="booking-calculator">
            <div className="max-w-5xl mx-auto px-gutter">
              <div className="rounded-lg bg-surface-container-lowest p-space-lg lg:p-space-xl shadow-xl">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center pb-space-md border-b border-outline gap-4">
                  <div>
                    <span className="px-3 py-1 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm uppercase font-bold">Interactive Tool</span>
                    <h2 className="font-headline-md text-headline-md text-primary mt-1">Instant Party Cost Estimator</h2>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">Calculate exact charges before picking your date &amp; time slot.</p>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded-full bg-surface-container text-on-surface-variant font-label-sm text-label-sm">
                    <span className="material-symbols-outlined text-secondary text-base">verified_user</span>
                    <span>No Hidden Taxes or Cleanup Charges</span>
                  </div>
                </div>

                {loading && (
                  <div className="pt-2 text-xs text-primary/70 flex items-center gap-1.5 animate-pulse">
                    <span className="material-symbols-outlined text-sm">sync</span>
                    <span>Syncing live pricing catalog...</span>
                  </div>
                )}

                {!loading && packages.length === 0 ? (
                  <p className="pt-6 font-body-md text-on-surface-variant">Booking stays closed until the host publishes packages.</p>
                ) : (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg pt-space-lg">
                  {/* Controls */}
                  <div className="lg:col-span-7 flex flex-col gap-space-md">
                    {/* Tier Selector */}
                    <div>
                      <label className="block font-label-md text-label-md text-primary mb-2 font-bold">1. Select Package Tier</label>
                      <div className="grid grid-cols-3 gap-2">
                        {['basic', 'gold', 'diamond'].map((code) => {
                          const isSel = calcTier === code;
                          const pkgItem = packages.find((p) => p.code === code);
                          const displayRate = pkgItem?.pricePerHourMinor
                            ? Math.round(pkgItem.pricePerHourMinor / 100).toLocaleString('en-IN')
                            : '—';
                          return (
                            <button
                              key={code}
                              type="button"
                              onClick={() => setCalcTier(code)}
                              className={`p-3 rounded-DEFAULT font-label-md text-label-md transition-all text-center capitalize ${
                                isSel
                                  ? 'bg-secondary text-on-secondary shadow-sm'
                                  : 'bg-surface-container-high text-primary hover:bg-surface-container-highest'
                              }`}
                            >
                              {code} (₹{displayRate})
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Hours Slider */}
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <label htmlFor="landing-duration-slider" className="font-label-md text-label-md text-primary font-bold">2. Booking Duration</label>
                        <span className="font-headline-sm text-headline-sm text-secondary font-bold">{calcHours} Hour{calcHours > 1 ? 's' : ''}</span>
                      </div>
                      <input
                        id="landing-duration-slider"
                        aria-label="Booking Duration in Hours"
                        type="range"
                        min="1"
                        max="6"
                        step="1"
                        value={calcHours}
                        onChange={(e) => setCalcHours(Number(e.target.value))}
                        className="w-full accent-secondary h-2 bg-surface-container-highest rounded-lg cursor-pointer"
                      />
                      <div className="flex justify-between text-xs text-on-surface-variant mt-1 font-mono">
                        <span>1 hr</span><span>2 hrs</span><span>3 hrs</span><span>4 hrs</span><span>5 hrs</span><span>6 hrs</span>
                      </div>
                    </div>

                    {/* Add-on Checkboxes */}
                    <div>
                      <label className="block font-label-md text-label-md text-primary mb-2 font-bold">3. Add-on Enhancements</label>
                      <div className="flex flex-col gap-2">
                        <label className="flex items-center justify-between p-3 rounded-DEFAULT bg-surface-container-low hover:bg-surface-container cursor-pointer transition-colors">
                          <div className="flex items-center gap-3">
                            <input
                              type="checkbox"
                              checked={selectedAddons.includes('bubble_entry')}
                              onChange={() => toggleAddon('bubble_entry')}
                              disabled={calcTier === 'diamond'}
                              className="w-5 h-5 accent-secondary rounded"
                            />
                            <div>
                              <p className="font-title-lg text-title-lg text-primary text-sm font-semibold">Bubble Machine Entry</p>
                              <p className="font-body-sm text-body-sm text-on-surface-variant text-xs">Continuous bubble drift during cake reveal</p>
                            </div>
                          </div>
                          <span className="font-label-sm text-label-sm text-secondary font-bold">
                            {calcTier === 'diamond' ? 'Included' : `+${bubblePrice}`}
                          </span>
                        </label>

                        <label className="flex items-center justify-between p-3 rounded-DEFAULT bg-surface-container-low hover:bg-surface-container cursor-pointer transition-colors">
                          <div className="flex items-center gap-3">
                            <input
                              type="checkbox"
                              checked={selectedAddons.includes('fog_entry')}
                              onChange={() => toggleAddon('fog_entry')}
                              disabled={calcTier === 'diamond'}
                              className="w-5 h-5 accent-secondary rounded"
                            />
                            <div>
                              <p className="font-title-lg text-title-lg text-primary text-sm font-semibold">Low Fog Cloud Entry</p>
                              <p className="font-body-sm text-body-sm text-on-surface-variant text-xs">Heavy floor-hugging dry smoke effect</p>
                            </div>
                          </div>
                          <span className="font-label-sm text-label-sm text-secondary font-bold">
                            {calcTier === 'diamond' ? 'Included' : `+${fogPrice}`}
                          </span>
                        </label>

                        <label className="flex items-center justify-between p-3 rounded-DEFAULT bg-surface-container-low hover:bg-surface-container cursor-pointer transition-colors">
                          <div className="flex items-center gap-3">
                            <input
                              type="checkbox"
                              checked={selectedAddons.includes('cold_fire_one_shot')}
                              onChange={() => toggleAddon('cold_fire_one_shot')}
                              disabled={calcTier === 'diamond'}
                              className="w-5 h-5 accent-secondary rounded"
                            />
                            <div>
                              <p className="font-title-lg text-title-lg text-primary text-sm font-semibold">Cold-Fire Spark Shot (1 blast)</p>
                              <p className="font-body-sm text-body-sm text-on-surface-variant text-xs">Indoor cold pyrotechnic spark fountain</p>
                            </div>
                          </div>
                          <span className="font-label-sm text-label-sm text-secondary font-bold">
                            {calcTier === 'diamond' ? 'Included' : `+${sparkPrice}`}
                          </span>
                        </label>
                      </div>
                    </div>
                  </div>

                  {/* Dynamic Server-Calculated Breakdown Card */}
                  <div className="lg:col-span-5 rounded-lg bg-surface-container-low p-space-md flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between pb-3 border-b border-outline">
                        <span className="font-title-lg text-title-lg text-primary">Summary Breakdown</span>
                        <span className="px-2.5 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm">Joybox Vadlamudi</span>
                      </div>
                      <div className="flex flex-col gap-2 my-4 font-body-sm text-body-sm text-on-surface">
                        {quoteError ? (
                          <div className="text-error text-xs p-2 rounded bg-error-container text-on-error-container">
                            {quoteError}
                          </div>
                        ) : quote ? (
                          quote.lineItems.map((item, idx) => (
                            <div key={idx} className="flex justify-between">
                              <span className={item.amountMinor < 0 ? 'text-secondary font-bold' : ''}>{item.description}</span>
                              <span className={item.amountMinor < 0 ? 'text-secondary font-bold' : 'font-semibold text-primary'}>
                                {item.amountMinor < 0 ? '-' : ''}₹{Math.abs(item.amountRupees).toLocaleString('en-IN')}
                              </span>
                            </div>
                          ))
                        ) : (
                          <div className="text-on-surface-variant">Calculating quote...</div>
                        )}
                        <div className="flex justify-between text-secondary font-semibold pt-2 border-t border-outline">
                          <span>AC &amp; Standard Decor</span>
                          <span>FREE / Included</span>
                        </div>
                      </div>
                    </div>

                    <div className="pt-4 border-t border-outline">
                      <div className="flex justify-between items-baseline mb-3">
                        <span className="font-label-lg text-label-lg text-on-surface-variant">Estimated Total:</span>
                        <span className="font-headline-lg text-headline-lg text-secondary">
                          ₹{quote ? quote.totalRupees.toLocaleString('en-IN') : '...'}
                        </span>
                      </div>
                      <Link
                        to={`/booking?package=${calcTier}&duration=${calcHours}`}
                        onClick={(e) => {
                          if (!BOOKINGS_OPEN) {
                            e.preventDefault();
                            const tierName = calcTier === 'diamond' ? 'Diamond' : calcTier === 'gold' ? 'Gold' : 'Basic';
                            setSelectedPackageForModal(tierName);
                          }
                        }}
                        className="w-full py-3.5 rounded-full bg-secondary text-on-secondary hover:bg-secondary-container font-label-md text-label-md text-center block transition-all shadow-md active:scale-95"
                      >
                        Proceed to Reserve Date &amp; Slot
                      </Link>
                      <p className="font-body-sm text-body-sm text-center text-on-surface-variant text-xs mt-2">
                        🔒 Slot is temporarily held upon selection while you complete details
                      </p>
                    </div>
                  </div>
                </div>
                )}
              </div>
            </div>
          </section>

          {/* REAL DECOR PHOTO GALLERY ATMOSPHERE */}
          <section className="w-full py-space-xl bg-surface-container-low">
            <div className="max-w-7xl mx-auto px-gutter">
              <div className="flex flex-col md:flex-row md:items-end justify-between mb-space-lg gap-4">
                <div>
                  <div className="flex items-center gap-2 text-secondary font-label-sm text-label-sm uppercase tracking-widest mb-1">
                    <span className="material-symbols-outlined text-base">photo_library</span>
                    <span>Real Decor Showcase</span>
                  </div>
                  <h2 className="font-headline-lg text-headline-lg text-primary tracking-tight">
                    Atmosphere &amp; Setups at Our Vadlamudi Hall
                  </h2>
                </div>
                <Link to="/gallery" className="inline-flex items-center gap-1.5 text-secondary font-label-md text-label-md hover:underline font-bold">
                  <span>Explore All Themes</span>
                  <span className="material-symbols-outlined text-base">arrow_forward</span>
                </Link>
              </div>

              {/* Bento photo grid with exact Stitch layout */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-md">
                <div className="group relative rounded-lg overflow-hidden shadow-md bg-surface-container aspect-square">
                  <img className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" alt="Peppa & Rainbow kids birthday theme setup" src="/images/placeholders/gallery-peppa-kids.jpg" />
                  <div className="absolute inset-x-0 bottom-0 bg-primary flex flex-col justify-end p-4">
                    <span className="font-label-sm text-label-sm text-tertiary-fixed font-bold">KIDS SPECIAL</span>
                    <p className="font-title-lg text-title-lg text-on-primary">Peppa &amp; Rainbow Theme</p>
                    <p className="font-body-sm text-body-sm text-primary-fixed text-xs">Actual setup in Vadlamudi venue</p>
                  </div>
                </div>
                <div className="group relative rounded-lg overflow-hidden shadow-md bg-surface-container aspect-square">
                  <img className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" alt="Chic Neon 21st birthday party setup" src="/images/placeholders/gallery-chic-neon.jpg" />
                  <div className="absolute inset-x-0 bottom-0 bg-primary flex flex-col justify-end p-4">
                    <span className="font-label-sm text-label-sm text-secondary-fixed font-bold">TEEN &amp; ADULT</span>
                    <p className="font-title-lg text-title-lg text-on-primary">Chic Neon 21st Birthday</p>
                    <p className="font-body-sm text-body-sm text-primary-fixed text-xs">Custom LED signage included</p>
                  </div>
                </div>
                <div className="group relative rounded-lg overflow-hidden shadow-md bg-surface-container aspect-square">
                  <img className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" alt="Warm fairy lights anniversary room setup" src="/images/placeholders/gallery-warm-anniversary.jpg" />
                  <div className="absolute inset-x-0 bottom-0 bg-primary flex flex-col justify-end p-4">
                    <span className="font-label-sm text-label-sm text-tertiary-fixed font-bold">COUPLES</span>
                    <p className="font-title-lg text-title-lg text-on-primary">Warm Gold Fairy Lights</p>
                    <p className="font-body-sm text-body-sm text-primary-fixed text-xs">Romantic &amp; peaceful setting</p>
                  </div>
                </div>
                <div className="group relative rounded-lg overflow-hidden shadow-md bg-surface-container aspect-square">
                  <img className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" alt="Private theater movie screening room" src="/images/placeholders/hero-hall-neon.jpg" />
                  <div className="absolute inset-x-0 bottom-0 bg-primary flex flex-col justify-end p-4">
                    <span className="font-label-sm text-label-sm text-secondary-fixed font-bold">SQUAD ADDA</span>
                    <p className="font-title-lg text-title-lg text-on-primary">Theater &amp; Movie Premiere</p>
                    <p className="font-body-sm text-body-sm text-primary-fixed text-xs">High-def projector &amp; sound</p>
                  </div>
                </div>
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

