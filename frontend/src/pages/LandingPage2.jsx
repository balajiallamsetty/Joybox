import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { VENUE_CONFIG } from '../services/config';

export default function LandingPage2() {
  const [lang] = useState('en');
  const [calcTier, setCalcTier] = useState('basic');
  const [calcHours, setCalcHours] = useState(2);
  const [addBubble, setAddBubble] = useState(false);
  const [addFog, setAddFog] = useState(false);
  const [addSpark, setAddSpark] = useState(false);
  const [activeOffer, setActiveOffer] = useState(null);
  const [packages, setPackages] = useState([]);
  const [addons, setAddons] = useState([]);
  const [quote, setQuote] = useState(null);

  useEffect(() => {
    Promise.all([
      api.getPackages().catch(() => ({ items: [] })),
      api.getAddOns().catch(() => ({ items: [] })),
      api.getActiveOffers().catch(() => ({ offers: [] }))
    ]).then(([pkgData, addonData, offerData]) => {
      setPackages(pkgData.items || []);
      setAddons(addonData.items || []);
      if (offerData.offers && offerData.offers.length > 0) {
        setActiveOffer(offerData.offers[0]);
      }
    });
  }, []);

  useEffect(() => {
    const selectedCodes = [];
    if (addBubble) selectedCodes.push('bubble_entry');
    if (addFog) selectedCodes.push('fog_entry');
    if (addSpark) selectedCodes.push('cold_fire_one_shot');

    api.getQuote({
      packageCode: calcTier,
      durationHours: Number(calcHours),
      addOnCodes: selectedCodes,
      applyPromo: true,
    })
      .then((data) => setQuote(data))
      .catch(() => {});
  }, [calcTier, calcHours, addBubble, addFog, addSpark]);

  const selectedPkg = packages.find((p) => p.code === calcTier);
  const hourlyRate = selectedPkg?.pricePerHourMinor
    ? Math.round(selectedPkg.pricePerHourMinor / 100)
    : (calcTier === 'basic' ? 999 : calcTier === 'gold' ? 1500 : 2500);

  const getAddonRate = (code, fallback) => {
    const a = addons.find((item) => item.code === code);
    return a?.priceMinor ? Math.round(a.priceMinor / 100) : fallback;
  };

  const t = (enText, teText) => (lang === 'te' ? teText : enText);

  const headingFontClass = 'font-fredoka';
  const bodyFontClass = 'font-poppins';

  return (
    <div className={`w-full min-h-screen bg-background text-on-surface antialiased selection:bg-secondary-fixed selection:text-on-secondary-fixed ${bodyFontClass}`}>
      {/* Top Notification Banner */}
      <header className="sticky top-0 left-0 w-full z-50" data-testid="site-navbar">
        <div className="h-20 w-full px-gutter bg-surface-container-lowest/85 backdrop-blur-xl shadow-[0_8px_24px_-4px_rgba(36,22,61,0.06),0_2px_6px_0_rgba(236,22,140,0.04)] flex items-center justify-between transition-all duration-300">
          <div className="flex items-center gap-space-md">
            <Link to="/" className="flex items-center gap-space-sm group">
              <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center text-on-secondary shadow-md group-hover:scale-105 transition-transform">
                <span className="material-symbols-outlined text-2xl">celebration</span>
              </div>
              <div className="flex flex-col">
                <span className={`${headingFontClass} text-headline-sm text-primary tracking-tight leading-none`}>Joybox</span>
                <span className="font-label-sm text-label-sm text-secondary leading-none uppercase tracking-wider font-bold">Party Room</span>
              </div>
            </Link>
            <div className="hidden xl:flex items-center gap-1 px-3 py-1 rounded-full bg-surface-container-low text-on-surface-variant font-label-sm text-label-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.8)]">
              <span className="material-symbols-outlined text-sm text-secondary">location_on</span>
              <span>Vadlamudi, Guntur (Beside Durga Mart)</span>
            </div>
          </div>

          <nav className="hidden lg:flex items-center gap-2 p-1.5 rounded-full bg-surface-container/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.8)]">
            <Link to="/" className="px-4 py-2 rounded-full font-label-md text-label-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-all">
              Landing 1
            </Link>
            <Link to="/landing-2" className="px-4 py-2 rounded-full transition-all bg-surface-container-high text-primary font-bold shadow-[inset_0_1px_2px_rgba(255,255,255,0.8)]">
              Landing 2
            </Link>
            <Link to="/packages" className="px-4 py-2 rounded-full font-label-md text-label-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-all">
              Packages & Add-ons
            </Link>
            <Link to="/booking" className="px-4 py-2 rounded-full font-label-md text-label-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-all">
              Book Venue
            </Link>
            <Link to="/gallery" className="px-4 py-2 rounded-full font-label-md text-label-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-all">
              Gallery
            </Link>
            <Link to="/contact" className="px-4 py-2 rounded-full font-label-md text-label-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-all">
              Contact
            </Link>
          </nav>

          <div className="flex items-center gap-space-sm">
            <a
              className="hidden md:flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-surface-container-low text-primary hover:bg-surface-container transition-all font-label-sm text-label-sm"
              href={`tel:${VENUE_CONFIG.whatsappNumber}`}
            >
              <span className="material-symbols-outlined text-base text-secondary">call</span>
              <span>+91 78427 04429</span>
            </a>
            <a
              className="hidden 2xl:flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-[#075E54] text-on-primary hover:opacity-95 transition-all font-label-sm text-label-sm shadow-[0_8px_20px_rgba(7,94,84,0.25)]"
              href={`https://wa.me/${VENUE_CONFIG.whatsappNumber}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="material-symbols-outlined text-base">chat</span>
              <span>WhatsApp Us</span>
            </a>
            <Link
              to="/booking"
              className="flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-secondary text-on-secondary hover:bg-secondary-container transition-all font-label-md text-label-md shadow-[0_8px_20px_rgba(180,0,104,0.35)] active:scale-95"
            >
              <span className="material-symbols-outlined text-base">confirmation_number</span>
              <span>{t('Book Now', 'బుక్ చేయండి')}</span>
            </Link>
          </div>
        </div>
      </header>

      <main className="w-full bg-background">
        {/* HERO SECTION */}
        <section className="relative w-full overflow-hidden bg-gradient-to-b from-primary-container via-primary to-surface-container-low text-on-primary pt-12 pb-space-xl">
          <div className="absolute -top-12 -left-20 w-96 h-96 rounded-full bg-secondary opacity-30 blur-3xl pointer-events-none"></div>
          <div className="absolute top-1/4 -right-16 w-80 h-80 rounded-full bg-tertiary-container opacity-25 blur-3xl pointer-events-none"></div>

          <div className="relative max-w-7xl mx-auto px-gutter">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-center pt-space-md">
              <div className="lg:col-span-7 flex flex-col text-left">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-surface-container-lowest/15 backdrop-blur-md shadow-md text-tertiary-fixed mb-space-sm w-fit">
                  <span className="material-symbols-outlined text-base animate-bounce" style={{ fontVariationSettings: "'FILL' 1" }}>celebration</span>
                  <span className="font-label-sm text-label-sm uppercase tracking-wider font-bold">
                    MAMA EDI MANA ADDA • VADLAMUDI, GUNTUR
                  </span>
                </div>
                {activeOffer && (
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-secondary text-on-secondary font-label-sm text-xs font-bold mb-space-sm w-fit shadow">
                    <span className="material-symbols-outlined text-sm">local_offer</span>
                    <span>{activeOffer.title || activeOffer.code} Promo Live</span>
                  </div>
                )}
                <h1 className={`${headingFontClass} text-4xl sm:text-5xl lg:text-6xl max-w-3xl tracking-tight leading-tight mb-space-sm font-extrabold`}>
                  Small Moments... <br />
                  <span className="text-tertiary-fixed">Big Celebrations!</span>
                </h1>
                <p className="font-body-lg text-body-lg text-primary-fixed max-w-xl mb-space-md leading-relaxed">
                  {t(
                    'Your neighborhood private AC celebration haven beside Durga Mart, Vadlamudi. Exclusively crafted for surprise birthdays, heartfelt anniversaries, reunion bashes, movie screenings, and intimate family milestones.',
                    'మీ వడ్లమూడి దుర్గా మార్ట్ పక్కనే ఉన్న ప్రైవేట్ ఎయిర్ కండిషన్డ్ పార్టీ హాల్. పుట్టినరోజులు, వార్షికోత్సవాలు, స్నేహితుల కలయికలు మరియు కుటుంబ వేడుకలకు ప్రత్యేకమైన వేదిక.'
                  )}
                </p>
                <div className="flex flex-wrap items-center gap-space-sm mb-space-md">
                  <Link
                    to="/booking"
                    className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-secondary text-on-secondary font-label-lg text-label-lg shadow-xl hover:bg-secondary-container transition-all hover:scale-105 active:scale-95"
                  >
                    <span className="material-symbols-outlined text-xl">calendar_month</span>
                    <span>{t('Check Live Availability & Slots', 'లైవ్ స్లాట్లు తనిఖీ చేయండి')}</span>
                  </Link>
                  <a
                    className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-[#075E54] text-on-primary font-label-lg text-label-lg shadow-lg hover:brightness-110 transition-all hover:scale-105 active:scale-95"
                    href={`https://wa.me/${VENUE_CONFIG.whatsappNumber}?text=Hi%20Joybox!%20I%20want%20to%20enquire%20about%20booking%20a%20private%20party%20slot%20in%20Vadlamudi.`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <span className="material-symbols-outlined text-xl">chat</span>
                    <span>Instant WhatsApp (+91 78427 04429)</span>
                  </a>
                  <a
                    className="flex items-center gap-2 px-5 py-3.5 rounded-full bg-surface-container-lowest/20 backdrop-blur-md text-on-primary font-label-md text-label-md shadow-md hover:bg-surface-container-lowest/30 transition-all"
                    href={`tel:${VENUE_CONFIG.whatsappNumber}`}
                  >
                    <span className="material-symbols-outlined text-lg text-tertiary-fixed">call</span>
                    <span>Call Host Kiran</span>
                  </a>
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-primary-fixed font-body-sm text-body-sm mb-space-md py-2 border-y border-outline">
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-secondary text-sm">ac_unit</span>
                    <span>100% Private AC Hall</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-secondary text-sm">check_circle</span>
                    <span>No Hidden Cleaning Fees</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-secondary text-sm">lock_clock</span>
                    <span>Zero Overlapping Bookings</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-secondary text-sm">restaurant</span>
                    <span>Outside Food & Catering Allowed</span>
                  </span>
                </div>

              </div>

              {/* Right Hero Visual */}
              <div className="lg:col-span-5 relative flex flex-col items-center">
                <div className="relative w-full max-w-md aspect-[4/5] rounded-lg overflow-hidden shadow-2xl bg-surface-container-high ring-2 ring-surface-container-lowest/30">
                  <img
                    className="w-full h-full object-cover"
                    alt="Joyful celebration party hall at Joybox Vadlamudi"
                    src="/images/placeholders/hero-hall-neon.jpg"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-primary/80 via-transparent to-transparent flex flex-col justify-end p-space-md">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded-full bg-secondary text-on-secondary font-label-sm text-label-sm font-bold text-xs">
                        Vadlamudi Adda
                      </span>
                      <span className="text-xs text-primary-fixed font-semibold">• Beside Durga Mart</span>
                    </div>
                    <p className={`${headingFontClass} text-headline-sm text-on-primary leading-tight font-bold`}>
                      Where Celebrations Feel Special & Exclusive
                    </p>
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


        {/* 3 PACKAGES SNAPSHOT SECTION */}
        <section className="w-full py-space-xl bg-background" id="packages-section">
          <div className="max-w-7xl mx-auto px-gutter">
            <div className="flex flex-col md:flex-row md:items-end justify-between mb-space-lg gap-4">
              <div>
                <div className="flex items-center gap-2 text-secondary font-label-sm text-label-sm uppercase tracking-widest mb-1">
                  <span className="material-symbols-outlined text-base">style</span>
                  <span>Tailored Celebration Packages</span>
                </div>
                <h2 className={`${headingFontClass} text-headline-lg text-primary tracking-tight font-bold`}>
                  Transparent Hourly Pricing, Zero Hidden Fees
                </h2>
              </div>
              <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
                Pick your ideal tier. Every booking guarantees entire private hall access for you and your guests.
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg items-stretch">
              {/* Basic Package */}
              <div className="rounded-lg bg-surface-container-low p-space-lg shadow-md flex flex-col justify-between transition-all hover:shadow-xl hover:-translate-y-1">
                <div>
                  <div className="flex justify-between items-start mb-space-sm">
                    <span className="px-3.5 py-1 rounded-full bg-primary-fixed text-primary font-label-sm text-label-sm uppercase font-bold">
                      Essential
                    </span>
                    <span className="font-label-sm text-label-sm text-on-surface-variant">Min. 1 Hour</span>
                  </div>
                  <h3 className={`${headingFontClass} text-headline-md text-primary mb-1 font-bold`}>Basic Tier</h3>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-md">
                    Perfect for intimate cake cutting, short surprise milestones, and quick family moments.
                  </p>
                  <div className="flex items-baseline gap-1 mb-space-md pb-space-sm bg-surface-container-lowest/60 p-3 rounded-DEFAULT">
                    <span className={`${headingFontClass} text-headline-lg text-primary font-bold`}>₹999</span>
                    <span className="font-body-md text-body-md text-on-surface-variant">/ hour</span>
                  </div>
                  <ul className="flex flex-col gap-3 font-body-sm text-body-sm text-on-surface mb-space-lg">
                    <li className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-secondary text-base">check_circle</span>
                      <span>Entire Air-Conditioned Private Hall</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-secondary text-base">check_circle</span>
                      <span>Curated Birthday / Occasion Theme Decor</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-secondary text-base">check_circle</span>
                      <span>High-output Sound System & Party Music</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-secondary text-base">check_circle</span>
                      <span>Vibrant Ambient Hall Lighting</span>
                    </li>
                  </ul>
                </div>
                <Link
                  to="/booking?package=basic"
                  className="w-full py-3.5 rounded-full bg-surface-container-high text-primary hover:bg-primary hover:text-on-primary font-label-md text-label-md text-center transition-all shadow-sm block font-bold"
                >
                  Select Basic (₹999/hr)
                </Link>
              </div>

              {/* Gold Package */}
              <div className="relative rounded-lg bg-surface-container-lowest p-space-lg shadow-xl flex flex-col justify-between -translate-y-2 transition-all hover:shadow-2xl">
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-5 py-1 rounded-full bg-tertiary-fixed text-on-tertiary-fixed font-label-sm text-label-sm uppercase tracking-widest shadow-md flex items-center gap-1 font-bold">
                  <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                  <span>Most Popular Choice</span>
                </div>
                <div>
                  <div className="flex justify-between items-start mb-space-sm mt-2">
                    <span className="px-3.5 py-1 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm uppercase font-bold">
                      Complete Party
                    </span>
                    <span className="font-label-sm text-label-sm text-secondary font-semibold">Bestseller</span>
                  </div>
                  <h3 className={`${headingFontClass} text-headline-md text-primary mb-1 font-bold`}>Gold Tier</h3>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-md">
                    The complete hassle-free party package. Cake, personalized display & decor all ready.
                  </p>
                  <div className="flex items-baseline gap-1 mb-space-md pb-space-sm bg-surface-container-low p-3 rounded-DEFAULT">
                    <span className={`${headingFontClass} text-headline-lg text-secondary font-bold`}>₹1,500</span>
                    <span className="font-body-md text-body-md text-on-surface-variant">/ hour</span>
                    <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed font-bold">
                      Includes 0.5kg Cake
                    </span>
                  </div>
                  <ul className="flex flex-col gap-3 font-body-sm text-body-sm text-on-surface mb-space-lg">
                    <li className="flex items-center gap-2 font-semibold text-primary">
                      <span className="material-symbols-outlined text-secondary text-base">done_all</span>
                      <span>Everything in Basic Package</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-secondary text-base">cake</span>
                      <span>Fresh 0.5 kg Birthday / Celebration Cake</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-secondary text-base">check_circle</span>
                      <span>Personalized Acrylic / Neon Name Display</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-secondary text-base">check_circle</span>
                      <span>Easel Stand Custom Welcome Chalkboard</span>
                    </li>
                  </ul>
                </div>
                <Link
                  to="/booking?package=gold"
                  className="w-full py-4 rounded-full bg-secondary text-on-secondary hover:bg-secondary-container font-label-md text-label-md text-center transition-all shadow-lg active:scale-95 block font-bold"
                >
                  Book Gold Package (₹1,500/hr)
                </Link>
              </div>

              {/* Diamond Package */}
              <div className="rounded-lg bg-primary-container text-on-primary p-space-lg shadow-lg flex flex-col justify-between transition-all hover:shadow-xl hover:-translate-y-1">
                <div>
                  <div className="flex justify-between items-start mb-space-sm">
                    <span className="px-3.5 py-1 rounded-full bg-tertiary text-on-tertiary font-label-sm text-label-sm uppercase font-bold">
                      VIP Cinematic
                    </span>
                    <span className="font-label-sm text-label-sm text-primary-fixed">Milestone Special</span>
                  </div>
                  <h3 className={`${headingFontClass} text-headline-md text-on-primary mb-1 font-bold`}>Diamond Tier</h3>
                  <p className="font-body-sm text-body-sm text-primary-fixed mb-space-md">
                    Spectacular grand entries with cinematic effects, cold spark shots, and fairytale bubbles.
                  </p>
                  <div className="flex items-baseline gap-1 mb-space-md pb-space-sm bg-primary/60 p-3 rounded-DEFAULT">
                    <span className={`${headingFontClass} text-headline-lg text-tertiary-fixed font-bold`}>₹2,500</span>
                    <span className="font-body-md text-body-md text-primary-fixed">/ hour</span>
                    <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-surface-container-lowest text-primary font-bold">
                      Cinematic FX
                    </span>
                  </div>
                  <ul className="flex flex-col gap-3 font-body-sm text-body-sm text-inverse-on-surface mb-space-lg">
                    <li className="flex items-center gap-2 font-semibold text-tertiary-fixed">
                      <span className="material-symbols-outlined text-base">done_all</span>
                      <span>Everything in Gold Package</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-tertiary-fixed text-base">bubble_chart</span>
                      <span>Magical Bubble Machine Entry</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-tertiary-fixed text-base">cloud</span>
                      <span>Cinematic Low-Lying Fog Cloud Entry</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-tertiary-fixed text-base">flare</span>
                      <span>1 Indoor Cold-Fire Spark Gun Blast</span>
                    </li>
                  </ul>
                </div>
                <Link
                  to="/booking?package=diamond"
                  className="w-full py-3.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed hover:bg-tertiary hover:text-on-tertiary font-label-md text-label-md text-center transition-all shadow-md block font-bold"
                >
                  Book Diamond Package (₹2,500/hr)
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* ADD-ONS SECTION */}
        <section className="w-full py-space-lg bg-surface-container-low">
          <div className="max-w-7xl mx-auto px-gutter">
            <div className="text-center max-w-2xl mx-auto mb-space-lg">
              <span className="font-label-sm text-label-sm text-secondary uppercase tracking-widest font-bold">Custom Sparkle</span>
              <h3 className={`${headingFontClass} text-headline-md text-primary font-bold`}>A-La-Carte Party Boosters</h3>
              <p className="font-body-sm text-body-sm text-on-surface-variant">Add magical grand elements to any package to personalize your celebration moment.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
              <div className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm flex items-center justify-between">
                <div className="flex items-center gap-space-sm">
                  <div className="w-12 h-12 rounded-full bg-primary-fixed flex items-center justify-center text-primary">
                    <span className="material-symbols-outlined text-2xl">bubble_chart</span>
                  </div>
                  <div>
                    <h4 className={`${headingFontClass} text-title-lg text-primary font-bold`}>Bubble Machine Entry</h4>
                    <p className="font-body-sm text-body-sm text-on-surface-variant text-xs">Magical floating bubbles for cake entry</p>
                  </div>
                </div>
                <span className="px-3 py-1 rounded-full bg-surface-container-high font-label-md text-label-md text-secondary font-bold">+₹300</span>
              </div>

              <div className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm flex items-center justify-between">
                <div className="flex items-center gap-space-sm">
                  <div className="w-12 h-12 rounded-full bg-secondary-fixed flex items-center justify-center text-secondary">
                    <span className="material-symbols-outlined text-2xl">cloud</span>
                  </div>
                  <div>
                    <h4 className={`${headingFontClass} text-title-lg text-primary font-bold`}>Low-Lying Fog Cloud</h4>
                    <p className="font-body-sm text-body-sm text-on-surface-variant text-xs">Dense floor mist for royal entry vibes</p>
                  </div>
                </div>
                <span className="px-3 py-1 rounded-full bg-surface-container-high font-label-md text-label-md text-secondary font-bold">+₹500</span>
              </div>

              <div className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm flex items-center justify-between">
                <div className="flex items-center gap-space-sm">
                  <div className="w-12 h-12 rounded-full bg-tertiary-fixed flex items-center justify-center text-tertiary">
                    <span className="material-symbols-outlined text-2xl">flare</span>
                  </div>
                  <div>
                    <h4 className={`${headingFontClass} text-title-lg text-primary font-bold`}>Cold-Fire Spark Gun</h4>
                    <p className="font-body-sm text-body-sm text-on-surface-variant text-xs">Safe indoor pyrotechnic spark blast</p>
                  </div>
                </div>
                <span className="px-3 py-1 rounded-full bg-surface-container-high font-label-md text-label-md text-secondary font-bold">+₹300 / shot</span>
              </div>
            </div>
          </div>
        </section>

        {/* INTERACTIVE PRICE ESTIMATOR */}
        <section className="w-full py-space-xl bg-background" id="booking-calculator">
          <div className="max-w-5xl mx-auto px-gutter">
            <div className="rounded-lg bg-surface-container-lowest p-space-lg lg:p-space-xl shadow-xl">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center pb-space-md border-b border-outline gap-4">
                <div>
                  <span className="px-3 py-1 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm uppercase font-bold">
                    Interactive Tool
                  </span>
                  <h2 className={`${headingFontClass} text-headline-md text-primary mt-1 font-bold`}>
                    Instant Party Cost Estimator
                  </h2>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">Calculate exact charges before picking your date & time slot.</p>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-full bg-surface-container text-on-surface-variant font-label-sm text-label-sm">
                  <span className="material-symbols-outlined text-secondary text-base">verified_user</span>
                  <span>No Hidden Taxes or Cleanup Charges</span>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg pt-space-lg">
                <div className="lg:col-span-7 flex flex-col gap-space-md">
                  <div>
                    <label className="block font-label-md text-label-md text-primary mb-2 font-bold">1. Select Package Tier</label>
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        className={`p-3 rounded-DEFAULT font-label-md text-label-md shadow-sm transition-all text-center ${
                          calcTier === 'basic' ? 'bg-secondary text-on-secondary font-bold' : 'bg-surface-container-high text-primary hover:bg-surface-container-highest'
                        }`}
                        onClick={() => setCalcTier('basic')}
                        type="button"
                      >
                        Basic (₹999)
                      </button>
                      <button
                        className={`p-3 rounded-DEFAULT font-label-md text-label-md transition-all text-center ${
                          calcTier === 'gold' ? 'bg-secondary text-on-secondary font-bold' : 'bg-surface-container-high text-primary hover:bg-surface-container-highest'
                        }`}
                        onClick={() => setCalcTier('gold')}
                        type="button"
                      >
                        Gold (₹1,500)
                      </button>
                      <button
                        className={`p-3 rounded-DEFAULT font-label-md text-label-md transition-all text-center ${
                          calcTier === 'diamond' ? 'bg-secondary text-on-secondary font-bold' : 'bg-surface-container-high text-primary hover:bg-surface-container-highest'
                        }`}
                        onClick={() => setCalcTier('diamond')}
                        type="button"
                      >
                        Diamond (₹2,500)
                      </button>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <label className="font-label-md text-label-md text-primary font-bold">2. Booking Duration</label>
                      <span className={`${headingFontClass} text-headline-sm text-secondary font-bold`}>{calcHours} Hours</span>
                    </div>
                    <input
                      className="w-full accent-secondary h-2 bg-surface-container-highest rounded-lg cursor-pointer"
                      max="6"
                      min="1"
                      step="1"
                      type="range"
                      value={calcHours}
                      onChange={(e) => setCalcHours(Number(e.target.value))}
                    />
                    <div className="flex justify-between text-xs text-on-surface-variant mt-1 font-mono">
                      <span>1 hr</span>
                      <span>2 hrs</span>
                      <span>3 hrs</span>
                      <span>4 hrs</span>
                      <span>5 hrs</span>
                      <span>6 hrs</span>
                    </div>
                  </div>

                  <div>
                    <label className="block font-label-md text-label-md text-primary mb-2 font-bold">3. Add-on Enhancements</label>
                    <div className="flex flex-col gap-2">
                      <label className="flex items-center justify-between p-3 rounded-DEFAULT bg-surface-container-low hover:bg-surface-container cursor-pointer transition-colors">
                        <div className="flex items-center gap-3">
                          <input
                            className="w-5 h-5 accent-secondary rounded"
                            type="checkbox"
                            checked={addBubble}
                            onChange={(e) => setAddBubble(e.target.checked)}
                          />
                          <div>
                            <p className="font-title-lg text-title-lg text-primary text-sm font-semibold">Bubble Machine Entry</p>
                            <p className="font-body-sm text-body-sm text-on-surface-variant text-xs">Continuous bubble drift during cake reveal</p>
                          </div>
                        </div>
                        <span className="font-label-sm text-label-sm text-secondary font-bold">+₹300</span>
                      </label>

                      <label className="flex items-center justify-between p-3 rounded-DEFAULT bg-surface-container-low hover:bg-surface-container cursor-pointer transition-colors">
                        <div className="flex items-center gap-3">
                          <input
                            className="w-5 h-5 accent-secondary rounded"
                            type="checkbox"
                            checked={addFog}
                            onChange={(e) => setAddFog(e.target.checked)}
                          />
                          <div>
                            <p className="font-title-lg text-title-lg text-primary text-sm font-semibold">Low Fog Cloud Entry</p>
                            <p className="font-body-sm text-body-sm text-on-surface-variant text-xs">Heavy floor-hugging dry smoke effect</p>
                          </div>
                        </div>
                        <span className="font-label-sm text-label-sm text-secondary font-bold">+₹500</span>
                      </label>

                      <label className="flex items-center justify-between p-3 rounded-DEFAULT bg-surface-container-low hover:bg-surface-container cursor-pointer transition-colors">
                        <div className="flex items-center gap-3">
                          <input
                            className="w-5 h-5 accent-secondary rounded"
                            type="checkbox"
                            checked={addSpark}
                            onChange={(e) => setAddSpark(e.target.checked)}
                          />
                          <div>
                            <p className="font-title-lg text-title-lg text-primary text-sm font-semibold">Cold-Fire Spark Shot (1 blast)</p>
                            <p className="font-body-sm text-body-sm text-on-surface-variant text-xs">Indoor cold pyrotechnic spark fountain</p>
                          </div>
                        </div>
                        <span className="font-label-sm text-label-sm text-secondary font-bold">+₹300</span>
                      </label>
                    </div>
                  </div>
                </div>

                {/* Summary Card */}
                <div className="lg:col-span-5 rounded-lg bg-surface-container-low p-space-md flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-outline">
                      <span className={`${headingFontClass} text-title-lg text-primary font-bold`}>Summary Breakdown</span>
                      <span className="px-2.5 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm font-bold">
                        Joybox Vadlamudi
                      </span>
                    </div>
                    <div className="flex flex-col gap-2 my-4 font-body-sm text-body-sm text-on-surface">
                      <div className="flex justify-between">
                        <span>
                          {calcTier.toUpperCase()} ({calcHours} hrs × ₹{hourlyRate})
                        </span>
                        <span className="font-semibold text-primary">
                          ₹
                          {quote
                            ? (quote.totalRupees !== undefined ? quote.baseAmountMinor / 100 : quote.baseAmountPaise / 100)
                            : hourlyRate * calcHours}
                        </span>
                      </div>
                      {addBubble && (
                        <div className="flex justify-between text-on-surface-variant">
                          <span>Bubble Entry</span>
                          <span>₹{getAddonRate('bubble_entry', 300)}</span>
                        </div>
                      )}
                      {addFog && (
                        <div className="flex justify-between text-on-surface-variant">
                          <span>Low Fog Cloud</span>
                          <span>₹{getAddonRate('fog_entry', 500)}</span>
                        </div>
                      )}
                      {addSpark && (
                        <div className="flex justify-between text-on-surface-variant">
                          <span>Cold Fire Shot</span>
                          <span>₹{getAddonRate('cold_fire_one_shot', 300)}</span>
                        </div>
                      )}
                      {quote && (quote.discountAmountMinor > 0 || quote.promoDiscountPaise > 0) && (
                        <div className="flex justify-between text-tertiary font-bold">
                          <span>Promo discount</span>
                          <span>- ₹{(quote.discountAmountMinor || quote.promoDiscountPaise) / 100}</span>
                        </div>
                      )}
                      <div className="flex justify-between text-secondary font-semibold pt-2 border-t border-outline">
                        <span>AC & Standard Decor</span>
                        <span>FREE / Included</span>
                      </div>
                    </div>
                  </div>
                  <div className="pt-4 border-t border-outline">
                    <div className="flex justify-between items-baseline mb-3">
                      <span className="font-label-lg text-label-lg text-on-surface-variant">Estimated Total:</span>
                      <span className={`${headingFontClass} text-headline-lg text-secondary font-extrabold`}>
                        ₹
                        {quote
                          ? (quote.totalRupees !== undefined ? quote.totalRupees : quote.totalAmountPaise / 100)
                          : hourlyRate * calcHours +
                            (addBubble ? getAddonRate('bubble_entry', 300) : 0) +
                            (addFog ? getAddonRate('fog_entry', 500) : 0) +
                            (addSpark ? getAddonRate('cold_fire_one_shot', 300) : 0)}
                      </span>
                    </div>
                    <Link
                      to={`/booking?package=${calcTier}&duration=${calcHours}`}
                      className="w-full py-3.5 rounded-full bg-secondary text-on-secondary hover:bg-secondary-container font-label-md text-label-md text-center block transition-all shadow-md active:scale-95 font-bold"
                    >
                      Proceed to Reserve Date & Slot
                    </Link>
                    <p className="font-body-sm text-body-sm text-center text-on-surface-variant text-xs mt-2">
                      🔒 Slot is temporarily held upon selection while you complete details
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* GALLERY SECTION */}
        <section className="w-full py-space-xl bg-surface-container-low" id="gallery-section">
          <div className="max-w-7xl mx-auto px-gutter">
            <div className="flex flex-col md:flex-row md:items-end justify-between mb-space-lg gap-4">
              <div>
                <div className="flex items-center gap-2 text-secondary font-label-sm text-label-sm uppercase tracking-widest mb-1 font-bold">
                  <span className="material-symbols-outlined text-base">photo_library</span>
                  <span>Real Decor Showcase</span>
                </div>
                <h2 className={`${headingFontClass} text-headline-lg text-primary tracking-tight font-bold`}>
                  Atmosphere & Setups at Our Vadlamudi Hall
                </h2>
              </div>
              <Link to="/gallery" className="inline-flex items-center gap-1.5 text-secondary font-label-md text-label-md hover:underline font-bold">
                <span>Explore All 20+ Themes</span>
                <span className="material-symbols-outlined text-base">arrow_forward</span>
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-md">
              <div className="group relative rounded-lg overflow-hidden shadow-md bg-surface-container aspect-square">
                <img
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  alt="Kids birthday celebration party hall setup"
                  src="/images/placeholders/gallery-peppa-kids.jpg"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-primary/80 via-transparent to-transparent flex flex-col justify-end p-4">
                  <span className="font-label-sm text-label-sm text-tertiary-fixed font-bold">KIDS SPECIAL</span>
                  <p className={`${headingFontClass} text-title-lg text-on-primary font-bold`}>Peppa & Rainbow Theme</p>
                  <p className="font-body-sm text-body-sm text-primary-fixed text-xs">Actual setup in Vadlamudi venue</p>
                </div>
              </div>

              <div className="group relative rounded-lg overflow-hidden shadow-md bg-surface-container aspect-square">
                <img
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  alt="Modern chic 21st birthday neon party backdrop"
                  src="/images/placeholders/gallery-chic-neon.jpg"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-primary/80 via-transparent to-transparent flex flex-col justify-end p-4">
                  <span className="font-label-sm text-label-sm text-secondary-fixed font-bold">TEEN & ADULT</span>
                  <p className={`${headingFontClass} text-title-lg text-on-primary font-bold`}>Chic Neon 21st Birthday</p>
                  <p className="font-body-sm text-body-sm text-primary-fixed text-xs">Custom LED signage included</p>
                </div>
              </div>

              <div className="group relative rounded-lg overflow-hidden shadow-md bg-surface-container aspect-square">
                <img
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  alt="Warm fairy lights anniversary celebration room"
                  src="/images/placeholders/gallery-warm-anniversary.jpg"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-primary/80 via-transparent to-transparent flex flex-col justify-end p-4">
                  <span className="font-label-sm text-label-sm text-tertiary-fixed font-bold">COUPLES</span>
                  <p className={`${headingFontClass} text-title-lg text-on-primary font-bold`}>Warm Gold Fairy Lights</p>
                  <p className="font-body-sm text-body-sm text-primary-fixed text-xs">Romantic & peaceful setting</p>
                </div>
              </div>

              <div className="group relative rounded-lg overflow-hidden shadow-md bg-surface-container aspect-square">
                <img
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  alt="Midnight glow DJ sound system celebration"
                  src="/images/placeholders/hero-hall-neon.jpg"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-primary/80 via-transparent to-transparent flex flex-col justify-end p-4">
                  <span className="font-label-sm text-label-sm text-secondary-fixed font-bold">REUNIONS & ADDA</span>
                  <p className={`${headingFontClass} text-title-lg text-on-primary font-bold`}>Midnight DJ Glow Party</p>
                  <p className="font-body-sm text-body-sm text-primary-fixed text-xs">Full Bluetooth audio authority</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* LOCATION & CONTACT SECTION */}
        <section className="w-full py-space-xl bg-background" id="location-section">
          <div className="max-w-7xl mx-auto px-gutter">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-center">
              <div className="lg:col-span-6 flex flex-col gap-space-md">
                <div>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm uppercase font-bold mb-2">
                    <span className="material-symbols-outlined text-base">verified</span>
                    <span>Physical Venue in Vadlamudi</span>
                  </div>
                  <h2 className={`${headingFontClass} text-headline-lg text-primary tracking-tight font-bold`}>
                    Easy to Reach, Right Beside Durga Mart
                  </h2>
                  <p className="font-body-md text-body-md text-on-surface-variant mt-2">
                    Centrally placed in Vadlamudi with convenient 2-wheeler and 4-wheeler parking space. Just 10 minutes from nearby colleges and major residential communities.
                  </p>
                </div>
                <div className="rounded-lg bg-surface-container-low p-space-md shadow-sm flex flex-col gap-3">
                  <div className="flex items-start gap-3">
                    <span className="material-symbols-outlined text-secondary text-2xl mt-0.5">location_on</span>
                    <div>
                      <p className={`${headingFontClass} text-title-lg text-primary font-bold`}>Joybox Party Room</p>
                      <p className="font-body-sm text-body-sm text-on-surface-variant">Beside Durga Mart, Main Road, Vadlamudi, Guntur District, Andhra Pradesh - 522213.</p>
                      <p className="font-label-sm text-label-sm text-secondary font-bold mt-1">తెలుగులో ల్యాండ్‌మార్క్: దుర్గా మార్ట్ పక్కనే, వడ్లమూడి</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 pt-3 border-t border-outline">
                    <span className="material-symbols-outlined text-secondary text-2xl">schedule</span>
                    <div>
                      <p className="font-body-sm text-body-sm text-on-surface font-semibold">Open Daily: 9:00 AM – 10:00 PM</p>
                      <p className="font-body-sm text-body-sm text-on-surface-variant text-xs">Pre-booked private slots locked exclusively for your party</p>
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-3">
                  <a
                    href={`https://wa.me/${VENUE_CONFIG.whatsappNumber}?text=Hi%20Kiran!%20I%20want%20to%20visit%20Joybox%20Party%20Room%20in%20Vadlamudi.`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-6 py-3 rounded-full bg-[#075E54] text-on-primary font-label-md text-label-md font-bold shadow-md hover:opacity-95"
                  >
                    <span className="material-symbols-outlined text-lg">chat</span>
                    <span>Chat with Host Kiran</span>
                  </a>
                  <a
                    href={`tel:${VENUE_CONFIG.whatsappNumber}`}
                    className="flex items-center gap-2 px-6 py-3 rounded-full bg-surface-container text-primary font-label-md text-label-md font-bold shadow-sm hover:bg-surface-container-high"
                  >
                    <span className="material-symbols-outlined text-lg text-secondary">call</span>
                    <span>+91 78427 04429</span>
                  </a>
                </div>
              </div>

              <div className="lg:col-span-6 rounded-lg overflow-hidden shadow-xl bg-surface-container aspect-video relative">
                <iframe
                  title="Joybox Location Vadlamudi"
                  src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d15318.423719941193!2d80.5484!3d16.2393!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3a4a098000000001%3A0x123456789abcdef!2sVadlamudi%2C%20Andhra%20Pradesh!5e0!3m2!1sen!2sin!4v1700000000000"
                  className="w-full h-full border-0"
                  allowFullScreen=""
                  loading="lazy"
                ></iframe>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="w-full bg-primary text-on-primary py-space-xl border-t border-primary-container">
        <div className="max-w-7xl mx-auto px-gutter flex flex-col md:flex-row items-center justify-between gap-space-md">
          <div className="flex flex-col items-center md:items-start">
            <span className={`${headingFontClass} text-2xl font-bold tracking-tight`}>Joybox Party Room</span>
            <p className="text-primary-fixed text-sm mt-1">Mama Edi Mana Adda • Vadlamudi, Guntur, AP</p>
          </div>
          <p className="text-xs text-primary-fixed/80">
            © {new Date().getFullYear()} Joybox Party Room. All rights reserved. Host: Kiran Kumar.
          </p>
        </div>
      </footer>
    </div>
  );
}

