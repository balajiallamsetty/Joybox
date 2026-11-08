import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Navigate, Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import BookingsClosedNotice from '../components/BookingsClosedNotice';
import { api } from '../services/api';
import { getMaxBookingDate } from '../utils/dateTime.js';

const API_BASE = import.meta?.env?.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api';

const PACKAGE_COPY = {
  basic: {
    tagline: 'Essential Celebration',
    badge: 'Essential',
    features: [
      'Entire Air-Conditioned Private Hall (100% Private)',
      'Curated Birthday / Occasion Theme Decor',
      'High-Output Surround Audio & Party Music',
      'Vibrant Ambient Hall Lighting',
      'Outside Food & Catering Allowed (Zero Cleanup Fee)',
    ],
  },
  gold: {
    tagline: 'Complete Party Experience',
    badge: 'Most Popular',
    features: [
      'Everything in Basic Package',
      'Fresh 0.5 kg Birthday / Celebration Cake Included',
      'Personalized Acrylic / Neon Name Display on Screen',
      'Easel Stand Custom Welcome Chalkboard',
      'Dedicated Table for Guest Treats & Gifts',
    ],
  },
  diamond: {
    tagline: 'VIP Cinematic Celebration',
    badge: 'VIP Ultimate',
    features: [
      'Everything in Gold Package',
      'Magical Bubble Machine Grand Entry',
      'Low-Lying Dense Fog Mist Entry Effect',
      'Safe Indoor Cold-Fire Pyrotechnic Spark Blast',
      'VIP Visuals & Dedicated Celebration Concierge',
    ],
  },
};

function mapServerPackage(serverPkg) {
  const copy = PACKAGE_COPY[serverPkg.code] || { tagline: serverPkg.name, features: [], badge: '' };
  const minor = Number(serverPkg.pricePerHourMinor || 0);
  return {
    code: serverPkg.code,
    name: serverPkg.name,
    pricePerHourMinor: minor,
    price: `₹${(minor / 100).toLocaleString('en-IN')}/hr`,
    tagline: copy.tagline,
    badge: copy.badge,
    desc: serverPkg.description || '',
    features: copy.features,
  };
}

const loadRazorpayScript = () => {
  return new Promise((resolve) => {
    if (typeof window !== 'undefined' && window.Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
};

const getTodayIST = () => {
  const istNow = new Date(Date.now() + 5.5 * 3600 * 1000);
  return istNow.toISOString().split('T')[0];
};

const getTomorrowIST = () => {
  const istNow = new Date(Date.now() + 5.5 * 3600 * 1000);
  istNow.setDate(istNow.getDate() + 1);
  return istNow.toISOString().split('T')[0];
};

export default function BookingWizardPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Resolve initial package param
  const refParam = searchParams.get('ref');
  const packageParam = searchParams.get('package');

  // Step 1: Package Selection, Step 2: Date & Slot, Step 3: Celebrant Info, Step 4: Verification
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedPackage, setSelectedPackage] = useState('');
  const [packages, setPackages] = useState([]);
  const [catalogLoaded, setCatalogLoaded] = useState(false);

  // Duration param (default 2 hrs)
  const [duration, setDuration] = useState(() => {
    const d = parseInt(searchParams.get('duration'), 10);
    return d >= 1 && d <= 6 ? d : 2;
  });

  // Date param (default tomorrow in IST or date in query)
  const [bookingDate, setBookingDate] = useState(() => {
    const d = searchParams.get('date');
    if (d && /^\d{4}-\d{2}-\d{2}$/.test(d)) return d;
    return getTomorrowIST();
  });

  // Live server quote states
  const [quote, setQuote] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState('');

  // Hydrate packages from server catalog on mount
  useEffect(() => {
    let cancelled = false;
    api.getPackages()
      .then((data) => {
        if (cancelled) return;
        const items = (data?.items || []).map(mapServerPackage);
        setPackages(items);
        const wanted = packageParam?.toLowerCase();
        const match = items.find((pkg) => pkg.code === wanted);
        const validInitialPackage = Boolean(match);
        if (match) {
          setSelectedPackage(match.code);
        } else if (items[0]) {
          setSelectedPackage(items[0].code);
        }
        setCurrentStep(validInitialPackage ? 2 : 1);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setCatalogLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [packageParam]);

  // Add-ons states
  const [availableAddOns, setAvailableAddOns] = useState([]);
  const [selectedAddOns, setSelectedAddOns] = useState(() => {
    const raw = searchParams.get('addons');
    if (!raw) return [];
    return raw.split(',').map((s) => s.trim().toLowerCase()).filter(Boolean);
  });

  // Public config states
  const [bookingsOpen, setBookingsOpen] = useState(true);
  const [whatsappNumber, setWhatsappNumber] = useState('917842704429');

  // Fetch server quote breakdown whenever selectedPackage, duration, or selectedAddOns change
  useEffect(() => {
    if (!selectedPackage) return undefined;
    let cancelled = false;
    setQuoteLoading(true);
    setQuoteError('');
    api.getQuote({
      packageCode: selectedPackage,
      durationHours: Number(duration),
      addOnCodes: selectedAddOns,
      applyPromo: true,
    })
      .then((data) => {
        if (!cancelled) {
          setQuote(data);
          setQuoteLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setQuoteError(err.message || 'Failed to fetch quote breakdown.');
          setQuoteLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPackage, duration, selectedAddOns]);

  const handleToggleAddOn = (code) => {
    setSelectedAddOns((prev) => {
      const next = prev.includes(code)
        ? prev.filter((c) => c !== code)
        : [...prev, code];
      setSearchParams(
        (spPrev) => {
          const sp = new URLSearchParams(spPrev);
          if (next.length > 0) {
            sp.set('addons', next.join(','));
          } else {
            sp.delete('addons');
          }
          return sp;
        },
        { replace: true }
      );
      return next;
    });
  };

  // Slot states
  const [availableSlots, setAvailableSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [slotError, setSlotError] = useState('');

  // Form info states
  const [celebrantName, setCelebrantName] = useState('');
  const [occasionType, setOccasionType] = useState('birthday');
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');

  // Submission & payment states
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [paymentsEnabled, setPaymentsEnabled] = useState(import.meta?.env?.VITE_PAYMENTS_ENABLED === 'true');

  useEffect(() => {
    let cancelled = false;
    api.getPublicConfig()
      .then((res) => {
        if (cancelled) return;
        const d = res?.data || res || {};
        if (d.paymentsEnabled !== undefined) {
          setPaymentsEnabled(Boolean(d.paymentsEnabled));
        }
        if (d.bookingsOpen !== undefined) {
          setBookingsOpen(Boolean(d.bookingsOpen));
        }
        if (d.whatsappNumber) {
          setWhatsappNumber(d.whatsappNumber);
        }
      })
      .catch(() => {});

    api.getAddOns()
      .then((res) => {
        if (cancelled) return;
        setAvailableAddOns(res?.items || []);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, []);

  // Keep selectedPackage synchronized with URL query changes if package param updates
  useEffect(() => {
    const p = searchParams.get('package');
    if (p) {
      const matched = packages.find((pkg) => pkg.code === p.toLowerCase());
      if (matched && matched.code !== selectedPackage) {
        setSelectedPackage(matched.code);
      }
    }
  }, [searchParams, packages, selectedPackage]);

  // Live availability fetch whenever bookingDate or duration changes
  // P1 Fix: Always reset selectedSlot when date or duration changes to prevent stale slots across dates
  useEffect(() => {
    let isCancelled = false;
    setSelectedSlot('');
    setIsLoadingSlots(true);
    setSlotError('');

    api.getAvailability(bookingDate, duration)
      .then((res) => {
        if (!isCancelled) {
          setAvailableSlots(res?.slots || []);
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          setSlotError(err.message || 'Could not load slots for this date.');
          setAvailableSlots([]);
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setIsLoadingSlots(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [bookingDate, duration]);

  // Package select action on Step 1: preselects package, updates URL, advances to Step 2
  const handleSelectPackage = (pkgCode) => {
    setSelectedPackage(pkgCode);
    setSelectedSlot('');
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set('package', pkgCode);
        return next;
      },
      { replace: true }
    );
    setCurrentStep(2);
  };

  const handleValidateToStep4 = () => {
    const cleanPhone = customerPhone.replace(/\D/g, '');
    if (!cleanPhone || cleanPhone.length < 10) {
      setErrorMessage('Please enter a valid 10-digit mobile number.');
      return;
    }
    setErrorMessage('');
    setCurrentStep(4);
  };

  const handleProceedToPayment = async () => {
    const cleanPhone = customerPhone.replace(/\D/g, '');
    if (!cleanPhone || cleanPhone.length < 10) {
      setErrorMessage('Please enter a valid 10-digit mobile or WhatsApp number.');
      setCurrentStep(3);
      return;
    }

    if (!selectedSlot) {
      setErrorMessage('Please choose an available time slot before continuing.');
      setCurrentStep(2);
      return;
    }

    if (!bookingsOpen) {
      setErrorMessage('Online bookings are currently closed. Please contact us via WhatsApp to reserve.');
      return;
    }

    setIsProcessing(true);
    setErrorMessage('');

    try {
      // 1. Create Booking with atomic slot claim
      const bookingPayload = {
        packageCode: selectedPackage,
        durationHours: Number(duration),
        date: bookingDate,
        startTime: selectedSlot,
        customerName: customerName.trim() || celebrantName.trim() || 'Guest',
        customerPhone: customerPhone.trim(),
        celebrantName: celebrantName.trim(),
        occasionType: occasionType || 'birthday',
        addOnCodes: selectedAddOns,
      };

      const bookingRes = await fetch(`${API_BASE}/bookings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bookingPayload),
      });
      const bookingJson = await bookingRes.json();
      if (!bookingRes.ok || !bookingJson.success) {
        throw new Error(bookingJson.error?.message || 'Failed to create booking reservation.');
      }

      const { bookingReference, accessToken } = bookingJson.data;
      try {
        sessionStorage.setItem(`booking_token_${bookingReference}`, accessToken);
      } catch (_e) {
        // ignore storage error
      }

      // If online payments are deferred/disabled, redirect immediately to booking confirmation
      if (!paymentsEnabled) {
        navigate(`/booking/${bookingReference}`);
        return;
      }

      // 2. Create Razorpay Payment Order
      const orderRes = await fetch(`${API_BASE}/payments/create-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bookingReference,
          token: accessToken,
        }),
      });
      const orderJson = await orderRes.json();
      if (!orderRes.ok || !orderJson.success) {
        if (orderJson.error?.code === 'PAYMENTS_DISABLED') {
          navigate(`/booking/${bookingReference}`);
          return;
        }
        throw new Error(orderJson.error?.message || 'Failed to initialize payment gateway.');
      }

      const { orderId, amountMinor, currency, keyId } = orderJson.data;

      // 3. Load Razorpay Checkout Script
      const isLoaded = await loadRazorpayScript();
      if (!isLoaded || !window.Razorpay) {
        // Fallback: If script blocked by browser or offline, redirect to status page
        navigate(`/booking/${bookingReference}`);
        return;
      }

      // 4. Open Razorpay Checkout Standard Modal
      const resolvedKey = keyId || import.meta?.env?.VITE_RAZORPAY_KEY_ID;
      if (!resolvedKey) {
        throw new Error('Payment gateway configuration error: Razorpay Key ID is not configured.');
      }

      const rzpOptions = {
        key: resolvedKey,
        amount: amountMinor,
        currency: currency || 'INR',
        name: 'Joybox Party Room',
        description: `${selectedPackage.toUpperCase()} Celebration Reservation`,
        order_id: orderId,
        handler: async function (response) {
          try {
            const verifyRes = await fetch(`${API_BASE}/payments/verify`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                bookingReference,
                token: accessToken,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              }),
            });
            const verifyJson = await verifyRes.json();
            if (verifyJson.success) {
              navigate(`/booking/${bookingReference}`);
            } else {
              setErrorMessage(verifyJson.error?.message || 'Payment verification failed.');
              setIsProcessing(false);
            }
          } catch (_err) {
            setErrorMessage('Network error during payment verification. Please check your booking status.');
            setIsProcessing(false);
          }
        },
        prefill: {
          name: customerName || celebrantName,
          contact: customerPhone,
        },
        theme: {
          color: '#1e0051',
        },
        modal: {
          ondismiss: function () {
            setIsProcessing(false);
          },
        },
      };

      const rzp = new window.Razorpay(rzpOptions);
      rzp.on('payment.failed', function (response) {
        setErrorMessage(response.error?.description || 'Payment failed or was cancelled.');
        setIsProcessing(false);
      });
      rzp.open();
    } catch (err) {
      setErrorMessage(err.message || 'An error occurred during reservation.');
      setIsProcessing(false);
    }
  };

  const currentPkgDetails = packages.find((p) => p.code === selectedPackage) || packages[0] || { name: '', price: '' };
  const selectedSlotObj = availableSlots.find((s) => s.startTime === selectedSlot);
  const slotEndTime = selectedSlotObj?.endTime || '';

  // If URL has ?ref=..., redirect directly to the booking status page
  if (refParam) {
    return <Navigate to={`/booking/${encodeURIComponent(refParam)}`} replace />;
  }

  return (
    <div className="w-full min-h-screen bg-background">
      <Header />
      <main className="w-full pt-20 bg-background">
        <div className="flex flex-col w-full">
          {/* Brand Geo-Banner & Live Concierge Ticker */}
          <div className="w-full bg-gradient-to-r from-primary-container via-primary to-primary-container text-on-primary py-space-xs px-margin-mobile lg:px-margin shadow-md">
            <div className="max-w-[1280px] mx-auto flex flex-wrap items-center justify-between gap-space-xs">
              <div className="flex items-center gap-space-xs">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed font-label-sm text-label-sm uppercase tracking-wide">
                  Local Adda
                </span>
                <span className="font-title-lg text-title-lg text-primary-fixed font-bold tracking-tight">Mama Edi Mana Adda</span>
                <span className="text-primary-fixed-dim text-body-sm hidden sm:inline">| Beside Durga Mart, Vadlamudi, Guntur</span>
              </div>
              <div className="flex items-center gap-space-sm">
                <div className="flex items-center gap-2 bg-on-primary/10 backdrop-blur-md px-3 py-1 rounded-full">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-secondary-container"></span>
                  </span>
                  <span className="font-label-sm text-label-sm text-primary-fixed font-medium">Host Kiran Kumar (+91 78427 04429) standing by for slot lock</span>
                </div>
              </div>
            </div>
          </div>

          {/* Wizard Main Content Wrapper */}
          <div className="w-full max-w-[1280px] mx-auto px-margin-mobile lg:px-margin py-space-lg">
            <div className="mb-space-lg flex flex-col md:flex-row md:items-end justify-between gap-space-sm">
              <div className="flex flex-col">
                <div className="flex items-center gap-2 mb-1">
                  <span className="material-symbols-outlined text-secondary text-[22px]">auto_awesome</span>
                  <span className="font-label-md text-label-md text-secondary uppercase font-bold tracking-wider">Joybox Party Room Vadlamudi</span>
                </div>
                <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Celebration Reservation Engine</h1>
                <p className="font-body-md text-body-md text-on-surface-variant max-w-2xl">
                  Reserve your private air-conditioned theater suite with custom projector nameplate, acoustic surround sound, and turnkey party special effects.
                </p>
              </div>
              <div className="flex items-center gap-space-xs bg-surface-container-high px-4 py-2 rounded-full shadow-sm">
                <span className="material-symbols-outlined text-tertiary text-[20px]">verified</span>
                <span className="font-label-sm text-label-sm text-on-surface font-semibold">100% Private Hall • Outside Food Allowed</span>
              </div>
            </div>

            {/* Bookings Closed Global Notification */}
            {!bookingsOpen && (
              <BookingsClosedNotice whatsappNumber={whatsappNumber} />
            )}

            {/* Stepper Navigation Bar: 1: Choose Package, 2: Date & Slot, 3: Celebrant Info, 4: Verification */}
            <div className="w-full mb-space-xl">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-space-xs p-1.5 bg-surface-container rounded-lg shadow-sm">
                {[
                  { num: 1, title: 'Choose Package', desc: 'Select Celebration Tier' },
                  { num: 2, title: 'Date & Slot', desc: 'Schedule & Live Availability' },
                  { num: 3, title: 'Celebrant Info', desc: 'Name Banner & Wishes' },
                  { num: 4, title: 'Verification', desc: 'Lock & Confirm' },
                ].map((s) => {
                  const isActive = currentStep === s.num;
                  const isCompleted = currentStep > s.num;
                  return (
                    <button
                      key={s.num}
                      type="button"
                      onClick={() => {
                        // Allow navigation to Step 1 or Step 2 anytime
                        if (s.num === 1 || s.num === 2) setCurrentStep(s.num);
                        // Navigation to Step 3 requires selected slot
                        else if (s.num === 3 && selectedSlot) setCurrentStep(3);
                        // Navigation to Step 4 requires valid phone and selected slot
                        else if (s.num === 4 && selectedSlot && customerPhone.trim().length >= 10) setCurrentStep(4);
                      }}
                      className={`flex items-center gap-space-xs px-3 py-2.5 rounded-DEFAULT transition-all ${
                        isActive
                          ? 'bg-surface-container-lowest text-primary shadow-[0_4px_12px_rgba(30,0,81,0.08)] font-bold'
                          : isCompleted
                          ? 'text-primary hover:bg-surface-container-lowest/50'
                          : 'text-on-surface-variant hover:text-primary'
                      }`}
                    >
                      <div
                        className={`w-7 h-7 rounded-full flex items-center justify-center font-label-sm text-label-sm font-bold ${
                          isActive
                            ? 'bg-primary text-on-primary'
                            : isCompleted
                            ? 'bg-secondary text-on-secondary'
                            : 'bg-surface-container-high text-on-surface-variant'
                        }`}
                      >
                        {isCompleted ? '✓' : s.num}
                      </div>
                      <div className="flex flex-col text-left">
                        <span className="font-label-sm text-label-sm font-bold leading-tight">{s.title}</span>
                        <span className="font-body-sm text-body-sm text-on-surface-variant text-[12px] leading-none">{s.desc}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Wizard Step Content */}
            <div className="rounded-lg bg-surface-container-lowest p-space-lg shadow-xl border border-outline">
              {/* STEP 1: CHOOSE PACKAGE */}
              {currentStep === 1 && (
                <div className="flex flex-col gap-6">
                  <div>
                    <h2 className="font-headline-md text-headline-md text-primary">Step 1: Choose Celebration Package</h2>
                    <p className="text-on-surface-variant text-sm mt-1">
                      Select your desired tier. You can customize add-ons or change your duration in the next step.
                    </p>
                  </div>

                  {catalogLoaded && packages.length === 0 ? (
                    <div className="rounded-2xl border border-outline bg-surface-container-low p-8 text-center">
                      <h3 className="font-title-lg text-title-lg text-primary font-bold">Bookings open soon</h3>
                      <p className="mt-2 text-on-surface-variant">
                        Packages and availability are not configured yet. Booking stays closed until the host publishes them.
                      </p>
                    </div>
                  ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {packages.map((pkg) => {
                      const isSelected = selectedPackage === pkg.code;
                      return (
                        <div
                          key={pkg.code}
                          onClick={() => handleSelectPackage(pkg.code)}
                          className={`p-6 rounded-2xl cursor-pointer border-2 transition-all flex flex-col justify-between ${
                            isSelected
                              ? 'border-secondary bg-surface-container-lowest shadow-xl ring-2 ring-secondary/20'
                              : 'border-outline bg-surface-container-low hover:border-secondary/40 hover:bg-surface-container'
                          }`}
                        >
                          <div>
                            <div className="flex justify-between items-start mb-2">
                              <span
                                className={`px-3 py-1 rounded-full font-label-sm text-label-sm uppercase font-bold ${
                                  pkg.code === 'diamond'
                                    ? 'bg-tertiary text-on-tertiary'
                                    : pkg.code === 'gold'
                                    ? 'bg-secondary text-on-secondary'
                                    : 'bg-primary text-on-primary'
                                }`}
                              >
                                {pkg.name} Tier
                              </span>
                              <span className="font-headline-sm text-headline-sm text-primary font-bold">{pkg.price}</span>
                            </div>
                            <h3 className="font-title-lg text-title-lg text-primary font-bold mt-2">{pkg.tagline}</h3>
                            <p className="text-sm text-on-surface-variant mt-1 mb-4">{pkg.desc}</p>
                            <ul className="flex flex-col gap-2 border-t border-outline pt-4 text-xs text-on-surface">
                              {pkg.features.map((feat, i) => (
                                <li key={i} className="flex items-center gap-2">
                                  <span className="material-symbols-outlined text-secondary text-sm">check_circle</span>
                                  <span>{feat}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          <div className="pt-6">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectPackage(pkg.code);
                              }}
                              className={`w-full py-3 rounded-full font-label-md text-label-md text-center transition-all shadow-md ${
                                isSelected
                                  ? 'bg-secondary text-on-secondary font-bold hover:bg-secondary-container'
                                  : 'bg-surface-container-high text-primary hover:bg-primary hover:text-on-primary'
                              }`}
                            >
                              {isSelected ? 'Selected • Continue to Date & Slot →' : `Select ${pkg.name}`}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  )}

                  {packages.length > 0 && (
                    <div className="rounded-2xl bg-surface-container-low border border-outline p-6 shadow-md flex flex-col gap-4 mt-2">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-outline">
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-secondary text-2xl">calculate</span>
                          <div>
                            <h3 className="font-title-lg text-title-lg font-bold text-primary">
                              Instant Cost Estimator for {currentPkgDetails.name} Tier
                            </h3>
                            <p className="text-xs text-on-surface-variant">
                              Preview total pricing based on your celebration duration before choosing dates and slots.
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-high text-xs font-bold text-primary">
                          <span className="material-symbols-outlined text-secondary text-sm">verified_user</span>
                          <span>No Hidden Fees</span>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                        <div className="flex flex-col gap-2">
                          <label className="text-xs font-bold text-primary uppercase tracking-wider">
                            Celebration Duration: <span className="text-secondary font-bold text-sm">{duration} Hour{duration > 1 ? 's' : ''}</span>
                          </label>
                          <div className="grid grid-cols-6 gap-2">
                            {[1, 2, 3, 4, 5, 6].map((h) => (
                              <button
                                key={h}
                                type="button"
                                onClick={() => setDuration(h)}
                                className={`py-2 rounded-lg text-xs font-bold transition-all text-center ${
                                  duration === h
                                    ? 'bg-secondary text-on-secondary shadow-sm'
                                    : 'bg-surface-container-high text-primary hover:bg-surface-container-highest'
                                }`}
                              >
                                {h} hr
                              </button>
                            ))}
                          </div>
                        </div>

                        <div className="rounded-xl bg-surface-container-lowest p-4 border border-outline flex flex-col justify-between gap-3">
                          <div className="flex justify-between items-center text-xs text-on-surface-variant pb-2 border-b border-outline">
                            <span>{currentPkgDetails.name} Tier ({duration} hr{duration > 1 ? 's' : ''} × {currentPkgDetails.price})</span>
                            <span className="font-bold text-primary">{currentPkgDetails.price}</span>
                          </div>
                          <div className="flex justify-between items-baseline">
                            <span className="text-sm font-bold text-primary">Estimated Total:</span>
                            <span className="font-headline-md text-headline-md font-bold text-secondary">
                              ₹{quote ? quote.totalRupees?.toLocaleString('en-IN') : Math.round((Number(currentPkgDetails.pricePerHourMinor || 0) * duration) / 100).toLocaleString('en-IN')}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex justify-end pt-2 border-t border-outline">
                        <button
                          type="button"
                          onClick={() => setCurrentStep(2)}
                          className="px-8 py-3 rounded-full bg-secondary text-on-secondary font-label-md text-label-md shadow-md hover:bg-secondary-container flex items-center gap-2"
                        >
                          <span>Continue with {currentPkgDetails?.name} Tier to Date &amp; Slot</span>
                          <span className="material-symbols-outlined text-lg">arrow_forward</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STEP 2: DATE & SLOT (LIVE AVAILABILITY WIRED) */}
              {currentStep === 2 && (
                <div className="flex flex-col gap-6">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <h2 className="font-headline-md text-headline-md text-primary">Step 2: Choose Date &amp; Time Slot</h2>
                      <p className="text-on-surface-variant text-sm mt-1">
                        Currently selecting for: <span className="font-bold text-secondary capitalize">{selectedPackage} Package</span> ({currentPkgDetails.price})
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setCurrentStep(1)}
                      className="text-xs font-bold text-secondary hover:underline flex items-center gap-1 self-start sm:self-auto"
                    >
                      <span className="material-symbols-outlined text-sm">edit</span>
                      <span>Change Package</span>
                    </button>
                  </div>

                  {/* SELECTED PACKAGE DETAILS & ALL-TIERS SWITCHER */}
                  <div className="rounded-2xl border border-outline bg-surface-container-low p-5 shadow-sm flex flex-col gap-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-outline">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-secondary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                          celebration
                        </span>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold uppercase tracking-wider text-secondary">
                              Selected Package
                            </span>
                            {currentPkgDetails.badge && (
                              <span className="text-[11px] px-2 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-bold">
                                {currentPkgDetails.badge}
                              </span>
                            )}
                          </div>
                          <h3 className="font-title-lg text-title-lg font-bold text-primary">
                            {currentPkgDetails.name} Tier — {currentPkgDetails.tagline || currentPkgDetails.name}
                          </h3>
                          <p className="text-xs text-on-surface-variant mt-0.5">{currentPkgDetails.desc}</p>
                        </div>
                      </div>
                      <div className="flex flex-col sm:items-end gap-1 shrink-0">
                        <span className="text-xs text-on-surface-variant font-medium">Switch Celebration Tier:</span>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {packages.map((pkg) => {
                            const isSel = pkg.code === selectedPackage;
                            return (
                              <button
                                key={pkg.code}
                                type="button"
                                onClick={() => {
                                  setSelectedPackage(pkg.code);
                                  setSearchParams(
                                    (prev) => {
                                      const next = new URLSearchParams(prev);
                                      next.set('package', pkg.code);
                                      return next;
                                    },
                                    { replace: true }
                                  );
                                }}
                                className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                                  isSel
                                    ? 'bg-secondary text-on-secondary shadow-md scale-105'
                                    : 'bg-surface-container-high text-primary hover:bg-surface-container-highest'
                                }`}
                              >
                                {pkg.name} ({pkg.price})
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </div>

                    {/* Included Features Grid */}
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-2 block">
                        Package Inclusions Guaranteed:
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                        {(currentPkgDetails.features || []).map((feat, i) => (
                          <div key={i} className="flex items-start gap-2 bg-surface-container-lowest/80 p-2.5 rounded-lg border border-outline-variant/40">
                            <span className="material-symbols-outlined text-secondary text-base shrink-0">check_circle</span>
                            <span className="text-xs font-medium text-on-surface">{feat}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* LIVE COST ESTIMATOR BAR */}
                  <div className="rounded-2xl bg-surface-container-lowest border-2 border-secondary/20 p-5 shadow-md flex flex-col gap-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-outline">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-secondary text-xl">calculate</span>
                        <h4 className="font-title-md text-title-md font-bold text-primary">Live Cost Estimator</h4>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-bold">
                          Server-Verified Quote
                        </span>
                      </div>
                      <div className="text-xs text-on-surface-variant flex items-center gap-2">
                        <span>{duration} hr{duration > 1 ? 's' : ''} duration</span>
                        <span>•</span>
                        <span>{selectedAddOns.length} add-on{selectedAddOns.length === 1 ? '' : 's'}</span>
                        <span>•</span>
                        <span className="text-secondary font-bold">No Hidden Fees</span>
                      </div>
                    </div>

                    {quoteLoading ? (
                      <div className="flex items-center gap-2 py-2 text-xs text-secondary font-medium animate-pulse">
                        <span className="material-symbols-outlined text-sm">sync</span>
                        <span>Recalculating live estimate from server...</span>
                      </div>
                    ) : quoteError ? (
                      <div className="text-xs p-2.5 rounded-lg bg-error-container text-on-error-container">
                        {quoteError}
                      </div>
                    ) : (
                      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pt-1">
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-on-surface-variant">
                          <span className="flex items-center gap-1 font-semibold text-primary">
                            <span>Base Rate:</span>
                            <span>{duration} hr{duration > 1 ? 's' : ''} × {currentPkgDetails.price}</span>
                          </span>
                          {selectedAddOns.length > 0 && (
                            <span className="flex items-center gap-1 text-secondary font-semibold">
                              <span>+ Add-ons ({selectedAddOns.length}):</span>
                              <span>
                                {selectedAddOns
                                  .map((c) => availableAddOns.find((a) => a.code === c)?.name || c)
                                  .join(', ')}
                              </span>
                            </span>
                          )}
                          {quote?.lineItems?.some((item) => item.amountMinor < 0) && (
                            <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold text-xs">
                              Promo Applied
                            </span>
                          )}
                        </div>

                        <div className="flex items-baseline justify-between md:justify-end gap-3 w-full md:w-auto shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-outline">
                          <span className="text-xs text-on-surface-variant font-medium">Estimated Total Payable:</span>
                          <span className="font-headline-md text-headline-md font-bold text-secondary">
                            ₹{quote ? quote.totalRupees?.toLocaleString('en-IN') : Math.round((Number(currentPkgDetails.pricePerHourMinor || 0) * duration) / 100).toLocaleString('en-IN')}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-surface-container-low p-4 rounded-xl">
                    <div>
                      <label htmlFor="bookingDateInput" className="block font-label-md text-label-md font-bold mb-2">Celebration Date</label>
                      <input
                        id="bookingDateInput"
                        type="date"
                        min={getTodayIST()}
                        max={getMaxBookingDate(new Date(Date.now() + 5.5 * 3600 * 1000), 90)}
                        value={bookingDate}
                        onChange={(e) => setBookingDate(e.target.value)}
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                        aria-label="Celebration Date"
                      />
                      <span className="text-xs text-on-surface-variant mt-1 block">
                        Dates are checked in real-time against booked slots and cleaning buffers.
                      </span>
                    </div>
                    <div>
                      <label htmlFor="durationSelect" className="block font-label-md text-label-md font-bold mb-2">Duration (Hours)</label>
                      <select
                        id="durationSelect"
                        value={duration}
                        onChange={(e) => setDuration(Number(e.target.value))}
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                        aria-label="Duration in hours"
                      >
                        {[1, 2, 3, 4, 5, 6].map((h) => (
                          <option key={h} value={h}>
                            {h} Hour{h > 1 ? 's' : ''}
                          </option>
                        ))}
                      </select>
                      <span className="text-xs text-on-surface-variant mt-1 block">
                        Standard slot durations from 1 to 6 hours.
                      </span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <label className="block font-label-md text-label-md font-bold">
                        Available Hourly Slots for {bookingDate} (9:00 AM – 10:00 PM IST)
                      </label>
                      {isLoadingSlots && (
                        <span className="text-xs text-secondary font-bold animate-pulse flex items-center gap-1">
                          <span className="material-symbols-outlined text-sm">sync</span>
                          <span>Checking slots...</span>
                        </span>
                      )}
                    </div>

                    {slotError && (
                      <div className="p-3 mb-4 rounded-lg bg-error-container text-on-error-container text-xs flex items-center gap-2">
                        <span className="material-symbols-outlined text-base">warning</span>
                        <span>{slotError}</span>
                      </div>
                    )}

                    {isLoadingSlots ? (
                      <div className="flex items-center justify-center p-8 bg-surface-container-low rounded-xl">
                        <div className="flex items-center gap-3 text-primary font-label-md">
                          <span className="inline-block animate-spin rounded-full h-5 w-5 border-2 border-primary border-t-transparent"></span>
                          <span>Loading live availability for {bookingDate}...</span>
                        </div>
                      </div>
                    ) : availableSlots.length > 0 ? (
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
                        {availableSlots.map((slot) => {
                          const isSelected = selectedSlot === slot.startTime;
                          const isAvailable = slot.available;
                          const badgeLabel = !isAvailable
                            ? slot.unavailableReason === 'booked'
                              ? 'Booked'
                              : slot.unavailableReason === 'hold'
                              ? 'Reserved'
                              : slot.unavailableReason === 'buffer'
                              ? 'Buffer'
                              : slot.unavailableReason === 'past'
                              ? 'Past'
                              : 'Unavailable'
                            : null;

                          return (
                            <button
                              key={slot.startTime}
                              type="button"
                              disabled={!isAvailable}
                              onClick={() => setSelectedSlot(slot.startTime)}
                              className={`p-3 rounded-lg flex flex-col items-center justify-center transition-all ${
                                !isAvailable
                                  ? 'bg-surface-container-low text-on-surface-variant cursor-not-allowed border border-outline'
                                  : isSelected
                                  ? 'bg-secondary text-on-secondary shadow-lg font-bold ring-2 ring-secondary scale-[1.02]'
                                  : 'bg-surface-container-high text-primary hover:bg-surface-container-highest cursor-pointer'
                              }`}
                            >
                              <span className="font-label-md text-label-md font-bold">{slot.startTime}</span>
                              <span className="text-[11px]">{slot.endTime ? `until ${slot.endTime}` : ''}</span>
                              {!isAvailable && (
                                <span className="mt-1 text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-surface-container-highest text-on-surface-variant">
                                  {badgeLabel}
                                </span>
                              )}
                            </button>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="p-6 text-center bg-surface-container-low rounded-xl text-on-surface-variant text-sm">
                        No slots available for {bookingDate}. Please try another date.
                      </div>
                    )}

                    <p className="text-xs text-on-surface-variant mt-3 flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm text-secondary">info</span>
                      <span>30-minute automated setup and sanitization buffer strictly enforced between bookings.</span>
                    </p>
                  </div>

                  {/* OPTIONAL ADD-ONS SELECTION */}
                  {availableAddOns.length > 0 && (
                    <div className="flex flex-col gap-3 pt-4 border-t border-outline" data-testid="wizard-addons-section">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                        <div>
                          <h3 className="font-title-md text-title-md font-bold text-primary">
                            Celebration Add-ons (Optional)
                          </h3>
                          <p className="text-xs text-on-surface-variant">
                            Elevate your event with special effects entries and party upgrades.
                          </p>
                        </div>
                        <Link
                          to="/add-ons"
                          target="_blank"
                          className="text-xs font-bold text-secondary hover:underline flex items-center gap-1 self-start sm:self-auto"
                        >
                          <span>View Add-on Details</span>
                          <span className="material-symbols-outlined text-xs">open_in_new</span>
                        </Link>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                        {availableAddOns.map((addon) => {
                          const isChecked = selectedAddOns.includes(addon.code);
                          const price = (addon.priceMinor || 0) / 100;
                          return (
                            <label
                              key={addon.code}
                              data-testid={`addon-checkbox-label-${addon.code}`}
                              className={`flex items-start gap-3 p-3.5 rounded-xl border-2 cursor-pointer transition-all ${
                                isChecked
                                  ? 'border-secondary bg-secondary/5 shadow-sm'
                                  : 'border-outline/50 bg-surface-container-low hover:border-secondary/40'
                              }`}
                            >
                              <input
                                type="checkbox"
                                name={`addon_${addon.code}`}
                                checked={isChecked}
                                onChange={() => handleToggleAddOn(addon.code)}
                                className="mt-1 w-4 h-4 text-secondary rounded border-outline focus:ring-secondary cursor-pointer"
                              />
                              <div className="flex flex-col flex-1">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-label-md font-bold text-primary text-sm">
                                    {addon.name}
                                  </span>
                                  <span className="font-label-md font-bold text-secondary text-sm">
                                    +₹{price.toLocaleString('en-IN')}
                                  </span>
                                </div>
                                <p className="text-xs text-on-surface-variant line-clamp-2 mt-0.5">
                                  {addon.description}
                                </p>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <div className="flex justify-between items-center pt-4 border-t border-outline">
                    <button
                      type="button"
                      onClick={() => setCurrentStep(1)}
                      className="px-6 py-3 rounded-full bg-surface-container-high text-primary font-label-md hover:bg-surface-container-highest transition-all"
                    >
                      ← Back to Packages
                    </button>
                    <button
                      type="button"
                      disabled={!selectedSlot || isLoadingSlots}
                      onClick={() => setCurrentStep(3)}
                      className="px-8 py-3 rounded-full bg-secondary text-on-secondary font-label-md shadow-md hover:bg-secondary-container transition-all flex items-center gap-2 disabled:bg-surface-container-high disabled:text-on-surface-variant disabled:cursor-not-allowed"
                    >
                      <span>Next: Celebrant Details</span>
                      <span className="material-symbols-outlined text-lg">arrow_forward</span>
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 3: CELEBRANT & CONTACT INFO */}
              {currentStep === 3 && (
                <div className="flex flex-col gap-6">
                  <div>
                    <h2 className="font-headline-md text-headline-md text-primary">Step 3: Celebrant &amp; Contact Info</h2>
                    <p className="text-on-surface-variant text-sm mt-1">
                      Provide details for the event projector banner, LED name display, and booking confirmation.
                    </p>
                  </div>

                  {errorMessage && (
                    <div className="p-3 rounded-lg bg-error-container text-on-error-container text-sm flex items-center gap-2">
                      <span className="material-symbols-outlined text-lg">error</span>
                      <span>{errorMessage}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="celebrantNameInput" className="block font-label-md text-label-md font-bold mb-2">Celebrant / Guest of Honor Name</label>
                      <input
                        id="celebrantNameInput"
                        type="text"
                        placeholder="e.g. Priya"
                        value={celebrantName}
                        onChange={(e) => setCelebrantName(e.target.value)}
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                        aria-label="Celebrant or Guest of Honor Name"
                      />
                      <span className="text-xs text-on-surface-variant mt-1 block">Featured on custom theater screen banner</span>
                    </div>

                    <div>
                      <label htmlFor="occasionTypeSelect" className="block font-label-md text-label-md font-bold mb-2">Occasion Type</label>
                      <select
                        id="occasionTypeSelect"
                        value={occasionType}
                        onChange={(e) => setOccasionType(e.target.value)}
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                        aria-label="Occasion Type"
                      >
                        <option value="birthday">Birthday Party</option>
                        <option value="anniversary">Anniversary Celebration</option>
                        <option value="reunion">Friends Reunion / Adda</option>
                        <option value="farewell">Farewell / Milestone</option>
                        <option value="family_event">Family Gathering</option>
                        <option value="other">Other Occasion</option>
                      </select>
                    </div>

                    <div>
                      <label htmlFor="customerNameInput" className="block font-label-md text-label-md font-bold mb-2">Your Full Name</label>
                      <input
                        id="customerNameInput"
                        type="text"
                        placeholder="e.g. Ravi Kumar"
                        value={customerName}
                        onChange={(e) => setCustomerName(e.target.value)}
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                        aria-label="Your Full Name"
                      >
                      </input>
                    </div>

                    <div>
                      <label htmlFor="customerPhoneInput" className="block font-label-md text-label-md font-bold mb-2">
                        Mobile / WhatsApp Number <span className="text-secondary">*</span>
                      </label>
                      <input
                        id="customerPhoneInput"
                        type="tel"
                        placeholder="e.g. 9876543210"
                        value={customerPhone}
                        onChange={(e) => setCustomerPhone(e.target.value)}
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                        required
                        aria-label="Mobile or WhatsApp Number"
                      />
                      <span className="text-xs text-on-surface-variant mt-1 block">Instant booking confirmation sent to this WhatsApp</span>
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-4 border-t border-outline">
                    <button
                      type="button"
                      onClick={() => setCurrentStep(2)}
                      className="px-6 py-3 rounded-full bg-surface-container-high text-primary font-label-md hover:bg-surface-container-highest transition-all"
                    >
                      ← Back to Date &amp; Slot
                    </button>
                    <button
                      type="button"
                      onClick={handleValidateToStep4}
                      className="px-8 py-3 rounded-full bg-secondary text-on-secondary font-label-md shadow-md hover:bg-secondary-container transition-all flex items-center gap-2"
                    >
                      <span>Next: Review &amp; Lock</span>
                      <span className="material-symbols-outlined text-lg">arrow_forward</span>
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 4: REVIEW & PAYMENT LOCK */}
              {currentStep === 4 && (
                <div className="flex flex-col gap-6">
                  <div>
                    <h2 className="font-headline-md text-headline-md text-primary">Step 4: Reservation Summary &amp; Lock</h2>
                    <p className="text-on-surface-variant text-sm mt-1">
                      Review your booking details before proceeding to instant payment and slot locking.
                    </p>
                  </div>

                  <div className="p-6 rounded-2xl bg-surface-container-low flex flex-col gap-3 border border-outline">
                    <div className="flex justify-between items-center pb-3 border-b border-outline">
                      <span className="font-medium text-on-surface-variant">Selected Package:</span>
                      <span className="font-bold text-primary capitalize text-base">
                        {currentPkgDetails.name} Tier ({currentPkgDetails.price})
                      </span>
                    </div>
                    <div className="flex justify-between items-center pb-3 border-b border-outline">
                      <span className="font-medium text-on-surface-variant">Scheduled Slot:</span>
                      <span className="font-bold text-primary text-base">
                        {bookingDate} at {selectedSlot} {slotEndTime ? `to ${slotEndTime}` : ''} ({duration} hr{duration > 1 ? 's' : ''})
                      </span>
                    </div>
                    <div className="flex justify-between items-center pb-3 border-b border-outline">
                      <span className="font-medium text-on-surface-variant">Celebrant &amp; Occasion:</span>
                      <span className="font-bold text-primary text-base">
                        {celebrantName || 'Guest of Honor'} ({occasionType})
                      </span>
                    </div>
                    <div className="flex justify-between items-center pb-3 border-b border-outline">
                      <span className="font-medium text-on-surface-variant">Contact Phone:</span>
                      <span className="font-bold text-primary text-base">{customerPhone}</span>
                    </div>

                    {selectedAddOns.length > 0 && (
                      <div className="flex justify-between items-center pb-3 border-b border-outline">
                        <span className="font-medium text-on-surface-variant">Selected Add-ons:</span>
                        <span className="font-bold text-primary text-base">
                          {selectedAddOns.map((code) => {
                            const found = availableAddOns.find((a) => a.code === code);
                            return found ? found.name : code;
                          }).join(', ')}
                        </span>
                      </div>
                    )}

                    {/* Live Server Quote Breakdown */}
                    <div className="pt-2 flex flex-col gap-2">
                      <span className="font-medium text-on-surface-variant text-sm">Price Breakdown:</span>
                      {quoteLoading ? (
                        <div className="text-xs text-on-surface-variant animate-pulse">Calculating server quote...</div>
                      ) : quoteError ? (
                        <div className="text-xs text-error font-medium p-2 rounded bg-error-container text-on-error-container">{quoteError}</div>
                      ) : quote ? (
                        <div className="flex flex-col gap-1.5 text-sm">
                          {quote.lineItems?.map((item, idx) => (
                            <div key={idx} className="flex justify-between items-center text-xs">
                              <span className={item.amountMinor < 0 ? 'text-secondary font-semibold' : 'text-on-surface'}>
                                {item.description}
                              </span>
                              <span className={item.amountMinor < 0 ? 'text-secondary font-semibold' : 'text-on-surface font-medium'}>
                                {item.amountMinor < 0 ? '-' : ''}₹{Math.abs(item.amountRupees).toLocaleString('en-IN')}
                              </span>
                            </div>
                          ))}
                          <div className="flex justify-between items-center pt-2 border-t border-outline font-bold text-base text-primary">
                            <span>Total Payable:</span>
                            <span className="text-secondary text-lg">₹{quote.totalRupees?.toLocaleString('en-IN')}</span>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  {errorMessage && (
                    <div className="p-4 rounded-lg bg-error-container text-on-error-container text-sm flex items-center gap-2">
                      <span className="material-symbols-outlined text-lg">error</span>
                      <span>{errorMessage}</span>
                    </div>
                  )}

                  {paymentsEnabled ? (
                    <div className="p-4 rounded-lg bg-surface-container-high text-on-surface text-sm flex items-center gap-3">
                      <span className="material-symbols-outlined text-secondary text-2xl">verified_user</span>
                      <span>
                        Direct online payment powered by Razorpay (UPI, Credit/Debit Cards, NetBanking). Your slot is atomically reserved and locked upon payment confirmation.
                      </span>
                    </div>
                  ) : (
                    <div className="p-4 rounded-lg bg-surface-container-high border border-outline text-on-surface text-sm flex items-center gap-3">
                      <span className="material-symbols-outlined text-secondary text-2xl">storefront</span>
                      <div>
                        <p className="font-bold text-primary">Pay-at-Venue Reservation</p>
                        <p className="text-on-surface-variant text-xs mt-0.5">
                          Online payment gateway is deferred. Confirm your slot now and pay the advance directly at the venue (Cash or UPI to Host Kiran Kumar).
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="flex flex-wrap justify-between items-center gap-4 pt-4 border-t border-outline">
                    <button
                      type="button"
                      onClick={() => setCurrentStep(3)}
                      className="px-6 py-3 rounded-full bg-surface-container-high text-primary font-label-md hover:bg-surface-container-highest transition-all"
                    >
                      ← Back
                    </button>
                    <div className="flex flex-wrap items-center gap-3">
                      <a
                        href={`https://wa.me/917842704429?text=Hi%20Kiran!%20I%20want%20to%20reserve%20Joybox%20on%20${bookingDate}%20at%20${selectedSlot}%20for%20${duration}%20hours%20(${selectedPackage}%20package).`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-5 py-3 rounded-full bg-[#075E54] text-on-primary font-label-md shadow-md hover:brightness-110 flex items-center gap-2"
                      >
                        <span className="material-symbols-outlined text-lg">chat</span>
                        <span>WhatsApp Host Kiran</span>
                      </a>
                      {!bookingsOpen ? (
                        <div
                          data-testid="bookings-closed-step4-alert"
                          className="px-5 py-3 rounded-full bg-amber-500/20 text-amber-900 border border-amber-500/40 text-xs font-bold flex items-center gap-1.5 shadow-sm"
                        >
                          <span className="material-symbols-outlined text-sm">lock</span>
                          <span>Online Bookings Closed • Contact on WhatsApp</span>
                        </div>
                      ) : (
                        <button
                          type="button"
                          disabled={isProcessing}
                          onClick={handleProceedToPayment}
                          className="px-8 py-3.5 rounded-full bg-secondary text-on-secondary font-label-md shadow-lg hover:bg-secondary-container transition-all flex items-center gap-2 disabled:bg-surface-container-high disabled:text-on-surface-variant"
                        >
                          {isProcessing ? (
                            <>
                              <span className="inline-block animate-spin rounded-full h-4 w-4 border-2 border-on-secondary border-t-transparent"></span>
                              <span>Securing Slot...</span>
                            </>
                          ) : paymentsEnabled ? (
                            <>
                              <span className="material-symbols-outlined text-lg">lock</span>
                              <span>Pay &amp; Lock Slot</span>
                            </>
                          ) : (
                            <>
                              <span className="material-symbols-outlined text-lg">check_circle</span>
                              <span>Confirm Reservation (Pay at Venue)</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
