import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { VENUE_CONFIG } from '../services/config';
import { api } from '../services/api';

export default function MobileBookingPage() {
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState('sat25');
  const [selectedSlot, setSelectedSlot] = useState('slotC');
  const [selectedTier, setSelectedTier] = useState('gold');
  const [fogSelected, setFogSelected] = useState(true);
  const [bubbleSelected, setBubbleSelected] = useState(true);
  const [sparkCount, setSparkCount] = useState(2);
  const [byoChecked, setByoChecked] = useState(true);
  const [tokenChecked, setTokenChecked] = useState(true);
  const [timeLeft, setTimeLeft] = useState(554); // 09:14 in seconds
  const [catalog, setCatalog] = useState(null);

  useEffect(() => {
    api.getPackages()
      .then((data) => setCatalog(data?.items || []))
      .catch(() => setCatalog([]));
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTimer = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Pricing calculation
  const serverTier = (catalog || []).find((pkg) => pkg.code === selectedTier);
  const hourlyRate = serverTier ? serverTier.pricePerHourMinor / 100 : null;
  const duration = 2; // hours
  const baseCost = (hourlyRate || 0) * duration;
  const fogCost = fogSelected ? 500 : 0;
  const bubbleCost = bubbleSelected ? 300 : 0;
  const sparkCost = sparkCount * 300;
  const totalBill = baseCost + fogCost + bubbleCost + sparkCost;
  const earlyBirdDiscount = 300;
  const netPayable = totalBill - earlyBirdDiscount;
  const rateLabel = hourlyRate == null ? '—' : `₹${Number(hourlyRate).toLocaleString('en-IN')}`;

  if (catalog && catalog.length === 0) {
    return (
      <div className="min-h-screen bg-background text-on-surface flex items-center justify-center p-8">
        <div className="max-w-md text-center">
          <h1 className="font-headline-md text-headline-md text-primary font-bold">Bookings open soon</h1>
          <p className="mt-2 text-on-surface-variant">
            Packages and availability are not configured yet. Booking stays closed until the host publishes them.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface font-body-md text-body-md text-on-surface flex flex-col min-h-screen selection:bg-secondary-fixed selection:text-on-secondary-fixed">
      {/* Header */}
      <header className="sticky top-0 inset-x-0 z-50 bg-surface/85 backdrop-blur-xl pt-safe shadow-[0_4px_20px_rgba(30,0,81,0.05)]">
        <div className="h-16 px-gutter-mobile flex items-center justify-between gap-space-xs">
          <div className="flex items-center gap-space-xs">
            <button
              aria-label="Go back"
              className="w-11 h-11 rounded-full bg-surface-container flex items-center justify-center text-primary active:scale-95 transition-transform"
              onClick={() => navigate(-1)}
            >
              <span className="material-symbols-outlined text-[20px]">arrow_back</span>
            </button>
            <div className="flex flex-col">
              <h1 className="font-headline-sm text-headline-sm text-primary font-bold tracking-tight truncate max-w-[200px]">
                Celebration Flow
              </h1>
              <span className="font-label-sm text-label-sm text-secondary font-semibold">Vadlamudi, Guntur</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              aria-label="Call venue"
              className="w-11 h-11 rounded-full bg-surface-container-high flex items-center justify-center text-primary active:scale-95 transition-transform shadow-[0_2px_8px_rgba(30,0,81,0.06)]"
              href={`tel:${VENUE_CONFIG.whatsappNumber}`}
            >
              <span className="material-symbols-outlined text-[20px]">call</span>
            </a>
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary">
              <span className="material-symbols-outlined text-[18px]">person</span>
            </div>
          </div>
        </div>
      </header>

      <main className="flex flex-col relative w-full pt-2 pb-safe bg-surface min-h-screen">
        <div className="flex flex-col w-full pb-28">
          {/* Verified Location & Urgency Strip */}
          <section className="px-gutter-mobile pt-space-xs pb-space-sm">
            <div className="bg-surface-container-high rounded-full px-4 py-2 flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-2 min-w-0">
                <span className="material-symbols-outlined text-secondary text-[18px] shrink-0" style={{ fontVariationSettings: "'FILL' 1" }}>
                  location_on
                </span>
                <span className="font-label-sm text-label-sm text-on-surface truncate">
                  Beside Durga Mart, Vadlamudi, Guntur
                </span>
              </div>
              <div className="flex items-center gap-1.5 shrink-0 pl-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-secondary"></span>
                </span>
                <span className="font-label-sm text-label-sm text-secondary font-bold tracking-tight">Fast Filling</span>
              </div>
            </div>
          </section>

          {/* 4-Step Celebration Wizard Pills */}
          <section className="px-gutter-mobile pb-space-sm">
            <nav aria-label="Booking Progress" className="bg-surface-container-low p-2 rounded-2xl shadow-[0_8px_24px_-4px_rgba(36,22,61,0.06)] flex items-center justify-between gap-1">
              {/* Step 1 */}
              <div className="flex-1 flex flex-col items-center py-1.5 px-1 rounded-xl bg-surface-container-highest">
                <div className="flex items-center gap-1">
                  <span className="w-5 h-5 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center text-[11px] font-bold">
                    <span className="material-symbols-outlined text-[13px]">check</span>
                  </span>
                  <span className="font-label-sm text-label-sm text-primary font-bold">Slots</span>
                </div>
                <span className="font-label-sm text-[10px] leading-3 text-secondary font-medium mt-0.5">2h Selected</span>
              </div>
              <span className="material-symbols-outlined text-on-surface-variant text-[16px]">chevron_right</span>

              {/* Step 2 */}
              <div className="flex-1 flex flex-col items-center py-1.5 px-1 rounded-xl bg-primary text-on-primary shadow-[0_4px_12px_rgba(30,0,81,0.18)]">
                <div className="flex items-center gap-1">
                  <span className="w-5 h-5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed flex items-center justify-center text-[11px] font-bold">2</span>
                  <span className="font-label-sm text-label-sm text-on-primary font-bold">Package</span>
                </div>
                <span className="font-label-sm text-[10px] leading-3 text-tertiary-fixed font-semibold mt-0.5">
                  {selectedTier.toUpperCase()}
                </span>
              </div>
              <span className="material-symbols-outlined text-on-surface-variant text-[16px]">chevron_right</span>

              {/* Step 3 */}
              <div className="flex-1 flex flex-col items-center py-1.5 px-1">
                <div className="flex items-center gap-1">
                  <span className="w-5 h-5 rounded-full bg-surface-variant text-on-surface-variant flex items-center justify-center text-[11px] font-bold">3</span>
                  <span className="font-label-sm text-label-sm text-on-surface font-bold">Details</span>
                </div>
                <span className="font-label-sm text-[10px] leading-3 text-on-surface-variant mt-0.5">Celebrant</span>
              </div>
              <span className="material-symbols-outlined text-on-surface-variant text-[16px]">chevron_right</span>

              {/* Step 4 */}
              <div className="flex-1 flex flex-col items-center py-1.5 px-1">
                <div className="flex items-center gap-1">
                  <span className="w-5 h-5 rounded-full bg-surface-variant text-on-surface-variant flex items-center justify-center text-[11px] font-bold">4</span>
                  <span className="font-label-sm text-label-sm text-on-surface font-bold">Advance</span>
                </div>
                <span className="font-label-sm text-[10px] leading-3 text-on-surface-variant mt-0.5">Instant Hold</span>
              </div>
            </nav>
          </section>

          {/* Slot Conflict Alert Banner */}
          <section className="px-gutter-mobile pb-space-sm">
            <div className="bg-error-container text-on-error-container p-3.5 rounded-2xl flex items-start gap-3 shadow-[0_8px_20px_-4px_rgba(186,26,26,0.14)]">
              <div className="w-8 h-8 rounded-full bg-error text-on-error flex items-center justify-center shrink-0 mt-0.5">
                <span className="material-symbols-outlined text-[18px]">bolt</span>
              </div>
              <div className="flex flex-col min-w-0">
                <span className="font-label-md text-label-md font-bold tracking-tight">Real-Time Slot Adjustment</span>
                <p className="font-body-sm text-body-sm leading-tight text-on-error-container mt-0.5">
                  7:00 PM was locked moments ago by another host. Reassigned smoothly to{' '}
                  <strong className="font-bold underline decoration-secondary">6:00 PM – 8:00 PM Prime Evening Slot</strong>.
                </p>
              </div>
            </div>
          </section>

          {/* Pending Timer Strip */}
          <section className="px-gutter-mobile pb-space-md">
            <div className="bg-surface-container rounded-2xl p-3 flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-full bg-tertiary-container text-on-tertiary-container flex items-center justify-center">
                  <span className="material-symbols-outlined text-[20px]">timer</span>
                </div>
                <div className="flex flex-col">
                  <span className="font-label-sm text-label-sm text-on-surface font-semibold">Slot Held on Server Lock</span>
                  <span className="font-body-sm text-[12px] text-on-surface-variant">
                    Expires in: <strong className="font-bold text-secondary">{formatTimer(timeLeft)}</strong> mins
                  </span>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-surface-container-highest text-primary font-label-sm text-[11px] font-bold">
                Step 2 of 4
              </span>
            </div>
          </section>

          {/* Core Booking Flow */}
          <div className="flex flex-col gap-space-lg px-gutter-mobile">
            {/* 1. Horizontal Date Strip */}
            <section className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-secondary text-[20px]">calendar_month</span>
                  <h2 className="font-headline-sm text-headline-sm text-primary font-bold">1. Select Celebration Date</h2>
                </div>
                <span className="font-label-sm text-label-sm text-secondary font-bold">Oct 2024</span>
              </div>
              <div className="flex gap-2.5 overflow-x-auto py-1.5 no-scrollbar -mx-gutter-mobile px-gutter-mobile">
                <button
                  className={`min-w-[76px] h-[82px] rounded-2xl p-2.5 flex flex-col items-center justify-between shadow-sm active:scale-95 transition-transform ${
                    selectedDate === 'thu23' ? 'bg-secondary text-on-secondary' : 'bg-surface-container'
                  }`}
                  onClick={() => setSelectedDate('thu23')}
                  type="button"
                >
                  <span className="font-label-sm text-label-sm opacity-80">Thu</span>
                  <span className="font-headline-md text-lg font-bold leading-none">23</span>
                  <span className="font-label-sm text-[11px] font-bold">₹1.2k/h</span>
                </button>

                <button
                  className={`min-w-[76px] h-[82px] rounded-2xl p-2.5 flex flex-col items-center justify-between shadow-sm active:scale-95 transition-transform ${
                    selectedDate === 'fri24' ? 'bg-secondary text-on-secondary' : 'bg-surface-container'
                  }`}
                  onClick={() => setSelectedDate('fri24')}
                  type="button"
                >
                  <span className="font-label-sm text-label-sm opacity-80">Fri</span>
                  <span className="font-headline-md text-lg font-bold leading-none">24</span>
                  <span className="font-label-sm text-[11px] font-bold">₹1.5k/h</span>
                </button>

                <button
                  className={`min-w-[84px] h-[82px] rounded-2xl p-2.5 flex flex-col items-center justify-between shadow-[0_8px_20px_rgba(184,13,104,0.35)] scale-105 transition-transform ${
                    selectedDate === 'sat25' ? 'bg-secondary text-on-secondary' : 'bg-surface-container'
                  }`}
                  onClick={() => setSelectedDate('sat25')}
                  type="button"
                >
                  <span className="font-label-sm text-label-sm font-semibold opacity-90">Sat</span>
                  <span className="font-headline-md text-lg font-bold leading-none">25</span>
                  <span className="px-2 py-0.5 rounded-full bg-surface text-secondary font-label-sm text-[10px] font-black tracking-wide uppercase">
                    Party Day
                  </span>
                </button>

                <div className="min-w-[76px] h-[82px] rounded-2xl bg-surface-container-high p-2.5 flex flex-col items-center justify-between cursor-not-allowed">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Sun</span>
                  <span className="font-headline-md text-lg font-bold text-on-surface-variant leading-none">26</span>
                  <span className="font-label-sm text-[10px] text-error font-bold tracking-tight">Sold Out</span>
                </div>

                <button
                  className={`min-w-[76px] h-[82px] rounded-2xl p-2.5 flex flex-col items-center justify-between shadow-sm active:scale-95 transition-transform ${
                    selectedDate === 'mon27' ? 'bg-secondary text-on-secondary' : 'bg-surface-container'
                  }`}
                  onClick={() => setSelectedDate('mon27')}
                  type="button"
                >
                  <span className="font-label-sm text-label-sm opacity-80">Mon</span>
                  <span className="font-headline-md text-lg font-bold leading-none">27</span>
                  <span className="font-label-sm text-[11px] font-bold">{rateLabel}/h</span>
                </button>
              </div>
            </section>

            {/* 2. Slot Grid with Strict States */}
            <section className="flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-secondary text-[20px]">schedule</span>
                  <h2 className="font-headline-sm text-headline-sm text-primary font-bold">2. Evening & Day Slots</h2>
                </div>
                <span className="font-label-sm text-label-sm text-on-surface-variant font-medium">Saturday Times</span>
              </div>
              <div className="flex flex-col gap-2.5">
                {/* Slot A: Available */}
                <button
                  className={`w-full p-3.5 rounded-2xl bg-surface-container-lowest shadow-[0_8px_24px_-4px_rgba(36,22,61,0.06)] flex items-center justify-between text-left active:scale-[0.99] transition-transform ${
                    selectedSlot === 'slotA' ? 'ring-2 ring-secondary' : ''
                  }`}
                  onClick={() => setSelectedSlot('slotA')}
                  type="button"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-surface-container-high text-primary flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-[20px]">sunny</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="font-title-lg text-title-lg text-primary font-bold">10:00 AM – 12:00 PM</span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant">Morning Matinee Celebration</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="font-label-lg text-label-lg text-primary font-bold">
                      ₹1,500<span className="text-xs font-normal text-on-surface-variant">/hr</span>
                    </span>
                    <span className="font-label-sm text-[11px] text-tertiary font-bold">Open</span>
                  </div>
                </button>

                {/* Slot B: Buffer */}
                <div className="w-full p-3.5 rounded-2xl bg-surface-container-low flex items-center justify-between cursor-not-allowed">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-surface-variant text-on-surface-variant flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-[20px]">sanitizer</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="font-title-lg text-title-lg text-on-surface-variant font-bold">02:30 PM – 03:00 PM</span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant">Sanitization, UV & Room Freshening Buffer</span>
                    </div>
                  </div>
                  <span className="font-label-sm text-label-sm text-on-surface-variant font-semibold px-2 py-1 rounded bg-surface-container-high">
                    Host Lock
                  </span>
                </div>

                {/* Slot C: Selected Prime Evening Block */}
                <div
                  className="w-full p-4 rounded-2xl bg-primary text-on-primary shadow-[0_16px_36px_-6px_rgba(53,16,120,0.22)] relative overflow-hidden cursor-pointer"
                  onClick={() => setSelectedSlot('slotC')}
                >
                  <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-secondary-container/20 rounded-full blur-xl pointer-events-none"></div>
                  <div className="flex items-start justify-between relative z-10">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-xl bg-secondary-container text-on-secondary-container flex items-center justify-center shrink-0 shadow-sm mt-0.5">
                        <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>stars</span>
                      </div>
                      <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                          <span className="font-title-lg text-title-lg text-on-primary font-bold">06:00 PM – 08:00 PM</span>
                        </div>
                        <span className="font-body-sm text-body-sm text-primary-fixed-dim">2 Hours Prime Evening Birthday Slot</span>
                        <span className="font-label-sm text-[12px] text-tertiary-fixed font-bold mt-1">Reassigned from 7:00 PM conflict</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end shrink-0">
                      <span className="px-2 py-0.5 rounded-full bg-secondary text-on-secondary font-label-sm text-[11px] font-bold shadow-sm">
                        Selected
                      </span>
                      <span className="font-title-lg text-title-lg text-tertiary-fixed font-bold mt-1">₹3,000</span>
                      <span className="font-label-sm text-[10px] text-primary-fixed-dim">₹1,500/hr × 2 hrs</span>
                    </div>
                  </div>
                </div>

                {/* Slot D: Booked */}
                <div className="w-full p-3.5 rounded-2xl bg-surface-container flex items-center justify-between cursor-not-allowed">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-surface-container-highest text-on-surface-variant flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-[20px]">lock</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="font-title-lg text-title-lg text-on-surface-variant font-bold">08:30 PM – 10:30 PM</span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant">Private Anniversary Screening (Pre-Booked)</span>
                    </div>
                  </div>
                  <span className="font-label-sm text-label-sm text-error font-bold">Booked</span>
                </div>
              </div>
            </section>

            {/* 3. Package Tier Carousel / Tiles */}
            <section className="flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-secondary text-[20px]">inventory_2</span>
                  <h2 className="font-headline-sm text-headline-sm text-primary font-bold">3. Celebration Package Tier</h2>
                </div>
                <span className="font-label-sm text-label-sm text-secondary font-semibold">Step 2 Active</span>
              </div>
              <div className="grid grid-cols-1 gap-3">
                <button
                  className={`w-full p-3.5 rounded-2xl flex items-center justify-between text-left transition-all ${
                    selectedTier === 'basic'
                      ? 'bg-secondary-fixed ring-2 ring-secondary'
                      : 'bg-surface-container-low'
                  }`}
                  onClick={() => setSelectedTier('basic')}
                  type="button"
                >
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className="font-title-lg text-title-lg text-primary font-bold">Basic Room Adda</span>
                      <span className="font-label-sm text-[11px] text-on-surface-variant font-semibold">Standard</span>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">Air-conditioned theatre, basic ambient RGB, 15 guest limit.</p>
                  </div>
                  <div className="flex flex-col items-end shrink-0 pl-2">
                    <span className="font-title-lg text-title-lg text-primary font-bold">{rateLabel}<span className="text-xs font-normal">/hr</span></span>
                  </div>
                </button>

                <button
                  className={`w-full p-3.5 rounded-2xl flex items-center justify-between text-left transition-all ${
                    selectedTier === 'gold'
                      ? 'bg-primary text-on-primary ring-2 ring-secondary shadow-md'
                      : 'bg-surface-container-low'
                  }`}
                  onClick={() => setSelectedTier('gold')}
                  type="button"
                >
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className="font-title-lg text-title-lg font-bold">Gold Gala Tier</span>
                      <span className="px-2 py-0.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed font-label-sm text-[10px] font-bold">
                        Bestseller
                      </span>
                    </div>
                    <p className={`font-body-sm text-body-sm mt-0.5 ${selectedTier === 'gold' ? 'text-primary-fixed' : 'text-on-surface-variant'}`}>
                      Includes 0.5kg cake, custom name neon banner & welcome board.
                    </p>
                  </div>
                  <div className="flex flex-col items-end shrink-0 pl-2">
                    <span className={`font-title-lg text-title-lg font-bold ${selectedTier === 'gold' ? 'text-tertiary-fixed' : 'text-secondary'}`}>
                      ₹1,500<span className="text-xs font-normal">/hr</span>
                    </span>
                  </div>
                </button>

                <button
                  className={`w-full p-3.5 rounded-2xl flex items-center justify-between text-left transition-all ${
                    selectedTier === 'diamond'
                      ? 'bg-secondary-fixed ring-2 ring-secondary'
                      : 'bg-surface-container-low'
                  }`}
                  onClick={() => setSelectedTier('diamond')}
                  type="button"
                >
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className="font-title-lg text-title-lg text-primary font-bold">Diamond VIP Tier</span>
                      <span className="font-label-sm text-[11px] text-secondary font-bold">Cinematic</span>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">Everything in Gold + Fog entry, bubble entry & cold-fire shots.</p>
                  </div>
                  <div className="flex flex-col items-end shrink-0 pl-2">
                    <span className="font-title-lg text-title-lg text-primary font-bold">₹2,500<span className="text-xs font-normal">/hr</span></span>
                  </div>
                </button>
              </div>
            </section>

            {/* 4. Add-ons Showcase */}
            <section className="flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-secondary text-[20px]">auto_awesome</span>
                  <h2 className="font-headline-sm text-headline-sm text-primary font-bold">4. A-La-Carte Boosters</h2>
                </div>
                <span className="font-label-sm text-label-sm text-secondary font-bold">Custom FX</span>
              </div>
              <div className="flex flex-col gap-2.5">
                <label className="w-full p-3 rounded-2xl bg-surface-container-high flex items-center justify-between shadow-sm cursor-pointer">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      className="w-5 h-5 rounded accent-secondary cursor-pointer"
                      checked={fogSelected}
                      onChange={(e) => setFogSelected(e.target.checked)}
                    />
                    <div className="flex flex-col">
                      <span className="font-title-lg text-title-lg text-primary font-bold">Fog Cloud Special Entry</span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant">Dense floor-hugging dry smoke mist</span>
                    </div>
                  </div>
                  <span className="font-label-md text-label-md text-secondary font-bold">+₹500</span>
                </label>

                <label className="w-full p-3 rounded-2xl bg-surface-container-high flex items-center justify-between shadow-sm cursor-pointer">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      className="w-5 h-5 rounded accent-secondary cursor-pointer"
                      checked={bubbleSelected}
                      onChange={(e) => setBubbleSelected(e.target.checked)}
                    />
                    <div className="flex flex-col">
                      <span className="font-title-lg text-title-lg text-primary font-bold">Party Bubble Streamer</span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant">Automatic high-density bubbles</span>
                    </div>
                  </div>
                  <span className="font-label-md text-label-md text-secondary font-bold">+₹300</span>
                </label>

                <div className="w-full p-3 rounded-2xl bg-surface-container-high flex items-center justify-between shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-surface-variant text-secondary flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>flare</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="font-title-lg text-title-lg text-primary font-bold">Indoor Cold-Fire Pyros</span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant">Smoke-free & completely safe sparkles (₹300/shot)</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 bg-surface rounded-full p-1 shadow-inner">
                    <button
                      aria-label="Decrease cold pyro shots"
                      className="w-8 h-8 rounded-full bg-surface-container text-primary flex items-center justify-center active:scale-95 font-bold"
                      type="button"
                      onClick={() => setSparkCount((prev) => Math.max(0, prev - 1))}
                    >
                      <span className="material-symbols-outlined text-[16px]">remove</span>
                    </button>
                    <span className="font-label-md text-label-md text-primary font-extrabold w-4 text-center">{sparkCount}</span>
                    <button
                      aria-label="Increase cold pyro shots"
                      className="w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center active:scale-95 font-bold"
                      type="button"
                      onClick={() => setSparkCount((prev) => prev + 1)}
                    >
                      <span className="material-symbols-outlined text-[16px]">add</span>
                    </button>
                  </div>
                </div>
              </div>
            </section>

            {/* 5. Celebrant & Policy Verification */}
            <section className="flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-secondary text-[20px]">badge</span>
                  <h2 className="font-headline-sm text-headline-sm text-primary font-bold">5. Celebrant & Policy Verification</h2>
                </div>
                <span className="font-label-sm text-label-sm text-tertiary font-bold">Pre-filled</span>
              </div>
              <div className="bg-surface-container-low p-4 rounded-2xl shadow-[0_8px_24px_-4px_rgba(36,22,61,0.06)] flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="font-label-sm text-label-sm text-on-surface-variant font-semibold">Celebrant Name & Occasion</label>
                  <div className="bg-surface-container-lowest px-3.5 py-3 rounded-xl flex items-center justify-between shadow-inner">
                    <span className="font-title-lg text-title-lg text-primary font-bold">Celebrant (7th Birthday)</span>
                    <span className="material-symbols-outlined text-secondary text-[20px]">edit</span>
                  </div>
                </div>
                <div className="flex flex-col gap-2 pt-1">
                  <label className="flex items-start gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      className="w-5 h-5 mt-0.5 rounded accent-secondary cursor-pointer"
                      checked={byoChecked}
                      onChange={(e) => setByoChecked(e.target.checked)}
                    />
                    <span className="font-body-sm text-body-sm text-on-surface leading-snug">
                      <strong>Approved BYO Food Policy:</strong> External cake, biryani & mocktails allowed. Outside heavy cooking or sterno heaters strictly prohibited.
                    </span>
                  </label>
                  <label className="flex items-start gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      className="w-5 h-5 mt-0.5 rounded accent-secondary cursor-pointer"
                      checked={tokenChecked}
                      onChange={(e) => setTokenChecked(e.target.checked)}
                    />
                    <span className="font-body-sm text-body-sm text-on-surface leading-snug">
                      <strong>Advance Payment Policy:</strong> Advance payment locks slot instantly with server verification. Host: Kiran Kumar.
                    </span>
                  </label>
                </div>
              </div>
            </section>

            {/* Interactive Price Calculation Accordion */}
            <section className="bg-surface-container-highest p-4 rounded-2xl shadow-sm flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="font-title-lg text-title-lg text-primary font-bold">Live Booking Calculation</span>
                <span className="font-label-sm text-label-sm text-secondary font-bold">Vadlamudi Prime Rates</span>
              </div>
              <div className="flex flex-col gap-1.5 text-body-sm text-on-surface-variant">
                <div className="flex justify-between">
                  <span>{selectedTier.toUpperCase()} Gala Tier ({duration} hrs × ₹{hourlyRate}/hr)</span>
                  <span className="font-semibold text-on-surface">₹{baseCost}</span>
                </div>
                {fogSelected && (
                  <div className="flex justify-between">
                    <span>Fog Cloud Special Entry</span>
                    <span className="font-semibold text-on-surface">₹{fogCost}</span>
                  </div>
                )}
                {bubbleSelected && (
                  <div className="flex justify-between">
                    <span>Party Bubble Streamer</span>
                    <span className="font-semibold text-on-surface">₹{bubbleCost}</span>
                  </div>
                )}
                {sparkCount > 0 && (
                  <div className="flex justify-between">
                    <span>Cold-Fire Spark Blasts ({sparkCount} shots)</span>
                    <span className="font-semibold text-on-surface">₹{sparkCost}</span>
                  </div>
                )}
                <div className="flex justify-between pt-1 text-primary font-bold">
                  <span className="font-title-lg text-title-lg">Total Party Bill</span>
                  <span className="font-title-lg text-title-lg text-secondary">₹{totalBill}</span>
                </div>
                <div className="flex justify-between text-tertiary font-medium">
                  <span>Early Bird Party Discount Applied</span>
                  <span>- ₹{earlyBirdDiscount}</span>
                </div>
                <div className="flex justify-between pt-1 text-primary font-black">
                  <span className="font-title-lg text-title-lg">Net Payable Amount</span>
                  <span className="font-headline-sm text-headline-sm text-primary font-extrabold">₹{netPayable}</span>
                </div>
              </div>
            </section>
          </div>

          {/* Persistent Bottom Action Bar */}
          <aside className="fixed bottom-0 inset-x-0 z-40 bg-surface-container-lowest/95 backdrop-blur-xl pb-safe shadow-[0_-8px_30px_rgba(30,0,81,0.12)]">
            <div className="px-gutter-mobile py-3 flex items-center justify-between gap-3">
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1 cursor-pointer">
                  <span className="font-headline-md text-xl text-primary font-extrabold leading-none">
                    ₹{netPayable}
                  </span>
                  <span className="material-symbols-outlined text-secondary text-[18px]">expand_less</span>
                </div>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="w-2 h-2 rounded-full bg-secondary"></span>
                  <span className="font-label-sm text-label-sm text-secondary font-bold truncate">
                    Pay Deposit Now
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <a
                  aria-label="Chat with Kiran on WhatsApp"
                  className="w-12 h-12 rounded-full bg-[#075E54] text-white flex items-center justify-center shadow-[0_4px_16px_rgba(7,94,84,0.3)] active:scale-95 transition-transform shrink-0"
                  href={`https://wa.me/${VENUE_CONFIG.whatsappNumber}?text=Hi%20Kiran,%20locking%20Gold%20tier%20at%20Joybox%20Vadlamudi%20for%20Celebrant`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <span className="material-symbols-outlined text-[24px]">chat</span>
                </a>
                <Link
                  to="/booking"
                  className="h-12 px-5 rounded-full bg-secondary text-on-secondary font-label-lg text-label-lg font-bold shadow-[0_8px_20px_rgba(184,13,104,0.35)] flex items-center gap-1.5 active:scale-95 transition-transform"
                >
                  <span>Continue</span>
                  <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
                </Link>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

