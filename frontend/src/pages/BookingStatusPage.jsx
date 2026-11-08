import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { VENUE_CONFIG } from '../services/config';
import { openRazorpayCheckout } from '../services/razorpay';

const isDev = Boolean(import.meta?.env?.DEV);

export default function BookingStatusPage() {
  const { ref } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const bookingRef = ref || searchParams.get('ref');

  // Preview state switcher is strictly DEV-ONLY.
  // In production builds (import.meta.env.PROD), searchParams.get('preview') is ignored completely.
  const previewParam = isDev ? searchParams.get('preview') : null;
  const [activeState, setActiveState] = useState(previewParam || (isDev ? 'confirmed' : 'lookup'));
  const [bookingData, setBookingData] = useState(null);
  const [loading, setLoading] = useState(Boolean(bookingRef));
  const [lookupInput, setLookupInput] = useState('');
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [paying, setPaying] = useState(false);
  const [payError, setPayError] = useState('');
  const [userToken, setUserToken] = useState('');
  const [cancelling, setCancelling] = useState(false);
  const [cancelMessage, setCancelMessage] = useState('');

  const handleCancelBooking = async () => {
    const resolvedToken = userToken || (typeof window !== 'undefined' ? sessionStorage.getItem(`booking_token_${bookingRef}`) : '');
    if (!bookingRef || !resolvedToken) return;
    const confirmCancel = window.confirm('Are you sure you want to cancel this reservation? The hall slot will be immediately released.');
    if (!confirmCancel) return;
    const reason = window.prompt('Please enter the cancellation reason (optional):') || 'Customer cancellation';
    setCancelling(true);
    try {
      const res = await fetch(`${import.meta?.env?.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api'}/bookings/${bookingRef}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: resolvedToken, reason }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error?.message || 'Cancellation failed');
      setActiveState('cancelled');
      setBookingData((prev) => ({
        ...prev,
        bookingStatus: 'cancelled',
        cancellationReason: reason,
      }));
      setCancelMessage('Booking cancelled successfully. Slot has been released.');
    } catch (err) {
      alert(err.message || 'Could not cancel booking.');
    } finally {
      setCancelling(false);
    }
  };

  const handlePayAdvance = async () => {
    setPaying(true);
    setPayError('');
    const token = sessionStorage.getItem(`booking_token_${bookingRef}`) || '';
    try {
      await openRazorpayCheckout({
        amount: bookingData?.advanceRequiredPaise || 50000,
        currency: 'INR',
        name: 'Joybox Party Room',
        description: `Advance Token for ${bookingRef || 'Booking'}`,
        prefill: {
          name: bookingData?.customerName || '',
          contact: bookingData?.customerPhone || '',
        },
        bookingReference: bookingRef,
        bookingToken: token,
        onSuccess: () => {
          setPaying(false);
          setActiveState('confirmed');
        },
        onFailure: (err) => {
          setPaying(false);
          setPayError(err.message || 'Payment could not be completed.');
        },
        onDismiss: () => {
          setPaying(false);
        },
      });
    } catch (err) {
      setPaying(false);
      setPayError(err.message || 'Failed to open Razorpay modal.');
    }
  };

  // When a real booking ref is passed, query API
  useEffect(() => {
    if (!bookingRef) {
      if (!isDev) {
        setActiveState('lookup');
      }
      setLoading(false);
      return;
    }
    setLoading(true);

    let token = searchParams.get('token');
    if (token) {
      setUserToken(token);
      try {
        sessionStorage.setItem(`booking_token_${bookingRef}`, token);
        // Scrub token from visible address bar without reloading
        const cleanUrl = `${window.location.pathname}?ref=${encodeURIComponent(bookingRef)}`;
        window.history.replaceState({}, document.title, cleanUrl);
      } catch (_e) {
        // storage disabled
      }
    } else {
      try {
        token = sessionStorage.getItem(`booking_token_${bookingRef}`) || '';
        if (token) setUserToken(token);
      } catch (_e) {
        token = '';
      }
    }

    const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : '';
    fetch(`${import.meta?.env?.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api'}/bookings/${bookingRef}${tokenQuery}`)
      .then(async (res) => {
        const json = await res.json();
        if (!res.ok) throw new Error(json?.error?.message || 'Booking not found');
        return json.data;
      })
      .then((data) => {
        setBookingData(data);
        if (data.bookingStatus) {
          setActiveState(data.bookingStatus);
        }
        setError('');
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setActiveState('not_found');
        setLoading(false);
      });
  }, [bookingRef, searchParams]);

  const copyBookingRef = () => {
    const textToCopy = bookingData?.bookingReference || (bookingRef ? `#${bookingRef}` : '#JBX-VDL-8429-CONF');
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleStateChange = (st) => {
    if (!isDev) return; // Strict guard: no effect in production
    setActiveState(st);
    const newParams = new URLSearchParams(searchParams);
    newParams.set('preview', st);
    setSearchParams(newParams);
  };

  const handleLookupSubmit = (e) => {
    e.preventDefault();
    if (!lookupInput.trim()) return;
    const cleanRef = lookupInput.trim().replace(/^#/, '');
    const newParams = new URLSearchParams(searchParams);
    newParams.set('ref', cleanRef);
    setSearchParams(newParams);
  };

  return (
    <div className="w-full min-h-screen bg-background font-body-md text-on-surface antialiased">
      <Header />
      <main className="w-full pt-20 bg-background">
        <div className="flex flex-col w-full">
          {/* Interactive State Simulator Floating Ribbon (ONLY RENDERED IN DEV MODE) */}
          {isDev && (
            <aside aria-label="Interactive State Preview Switcher" className="w-full bg-surface-container py-3 shadow-sm border-b border-outline">
              <div className="max-w-[1280px] mx-auto px-margin-mobile lg:px-margin flex flex-col md:flex-row items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary text-on-primary">
                    <span className="material-symbols-outlined text-[15px]">tune</span>
                  </span>
                  <span className="font-label-md text-label-md text-primary font-bold">Booking Status State Switcher (Dev Mode Only):</span>
                  <span className="hidden sm:inline font-body-sm text-body-sm text-on-surface-variant">
                    Disabled in production builds
                  </span>
                </div>
                <div className="flex items-center gap-1.5 p-1 bg-surface-container-highest rounded-full overflow-x-auto max-w-full">
                  <button
                    className={`px-space-sm py-1.5 rounded-full font-label-sm text-label-sm font-semibold transition-all flex items-center gap-1 ${
                      activeState === 'confirmed'
                        ? 'bg-secondary text-on-secondary shadow-md'
                        : 'text-on-surface-variant hover:text-on-surface'
                    }`}
                    onClick={() => handleStateChange('confirmed')}
                  >
                    <span className="material-symbols-outlined text-[15px]" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
                    <span>1. Confirmed</span>
                  </button>
                  <button
                    className={`px-space-sm py-1.5 rounded-full font-label-sm text-label-sm font-semibold transition-all flex items-center gap-1 ${
                      activeState === 'inquiry'
                        ? 'bg-secondary text-on-secondary shadow-md'
                        : 'text-on-surface-variant hover:text-on-surface'
                    }`}
                    onClick={() => handleStateChange('inquiry')}
                  >
                    <span className="material-symbols-outlined text-[15px]">schedule</span>
                    <span>2. Inquiry Review</span>
                  </button>
                  <button
                    className={`px-space-sm py-1.5 rounded-full font-label-sm text-label-sm font-semibold transition-all flex items-center gap-1 ${
                      activeState === 'pending'
                        ? 'bg-secondary text-on-secondary shadow-md'
                        : 'text-on-surface-variant hover:text-on-surface'
                    }`}
                    onClick={() => handleStateChange('pending')}
                  >
                    <span className="material-symbols-outlined text-[15px]">pending</span>
                    <span>3. Pay Token</span>
                  </button>
                  <button
                    className={`px-space-sm py-1.5 rounded-full font-label-sm text-label-sm font-semibold transition-all flex items-center gap-1 ${
                      activeState === 'failed'
                        ? 'bg-secondary text-on-secondary shadow-md'
                        : 'text-on-surface-variant hover:text-on-surface'
                    }`}
                    onClick={() => handleStateChange('failed')}
                  >
                    <span className="material-symbols-outlined text-[15px]">error_outline</span>
                    <span>4. Session Failed</span>
                  </button>
                </div>
              </div>
            </aside>
          )}

          {/* PRODUCTION / ERROR / LOOKUP STATES */}
          {(!bookingData && (!isDev || activeState === 'not_found' || (bookingRef && loading))) && (
            <section className="relative w-full max-w-[1280px] mx-auto px-margin-mobile lg:px-margin py-space-xl flex flex-col items-center">
              {loading ? (
                <div className="p-space-xl rounded-lg bg-surface-container-lowest shadow-md text-center max-w-lg w-full">
                  <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-secondary border-t-transparent mb-3"></div>
                  <h2 className="font-headline-sm text-headline-sm text-primary font-bold">Verifying Booking Status</h2>
                  <p className="text-on-surface-variant text-sm mt-1">Connecting to Joybox server...</p>
                </div>
              ) : activeState === 'not_found' ? (
                <div className="p-space-xl rounded-lg bg-surface-container-lowest shadow-xl flex flex-col items-center text-center max-w-lg w-full gap-3">
                  <div className="w-16 h-16 rounded-full bg-error-container text-error flex items-center justify-center">
                    <span className="material-symbols-outlined text-3xl">cancel</span>
                  </div>
                  <h2 className="font-headline-md text-headline-md text-primary font-bold">Booking Not Found</h2>
                  <p className="text-on-surface-variant text-sm">
                    {error || `No booking found matching reference "${bookingRef}". Please check your code or contact Host Kiran Kumar.`}
                  </p>
                  <div className="flex flex-wrap justify-center gap-3 mt-3">
                    <button
                      onClick={() => setActiveState('lookup')}
                      className="px-5 py-2.5 rounded-full bg-surface-container-high text-primary font-label-md text-label-md font-bold"
                    >
                      Try Another Code
                    </button>
                    <a
                      href={`https://wa.me/${VENUE_CONFIG.whatsappNumber}?text=Hi%20Kiran!%20I%20have%20an%20inquiry%20about%20my%20booking%20reference%20${bookingRef || ''}.`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-5 py-2.5 rounded-full bg-[#075E54] text-on-primary font-label-md text-label-md font-bold"
                    >
                      WhatsApp Host Kiran
                    </a>
                  </div>
                </div>
              ) : (
                /* Lookup Form */
                <div className="p-space-xl rounded-lg bg-surface-container-lowest shadow-xl flex flex-col items-center text-center max-w-lg w-full gap-4">
                  <div className="w-16 h-16 rounded-full bg-primary flex items-center justify-center text-secondary-fixed shadow-md">
                    <span className="material-symbols-outlined text-3xl">search</span>
                  </div>
                  <div>
                    <h2 className="font-headline-md text-headline-md text-primary font-bold">Track Your Celebration Booking</h2>
                    <p className="text-on-surface-variant text-sm mt-1">
                      Enter your booking reference from your SMS or WhatsApp confirmation.
                    </p>
                  </div>
                  <form onSubmit={handleLookupSubmit} className="w-full flex flex-col gap-3">
                    <input
                      type="text"
                      value={lookupInput}
                      onChange={(e) => setLookupInput(e.target.value)}
                      placeholder="e.g. JBX-VDL-8429-CONF"
                      className="w-full px-4 py-3 rounded-full border border-outline-variant bg-surface text-on-surface font-mono text-center text-base focus:outline-none focus:ring-2 focus:ring-secondary"
                      required
                    />
                    <button
                      type="submit"
                      className="w-full py-3.5 rounded-full bg-secondary text-on-secondary font-label-lg text-label-lg font-bold shadow-md hover:bg-secondary-container transition-all"
                    >
                      Check Status
                    </button>
                  </form>
                </div>
              )}
            </section>
          )}

          {/* RENDER ACTIVE STATUS VIEW (IN DEV OR WHEN VALID SERVER DATA EXISTS) */}
          {activeState !== 'not_found' && (isDev || bookingData) && (
            <>
              {/* Top Hero / Banner Status Section */}
              <section className="relative w-full overflow-hidden pt-space-md pb-space-lg bg-gradient-to-b from-surface-container-low via-surface to-background">
                <div aria-hidden="true" className="absolute inset-0 pointer-events-none opacity-40 select-none overflow-hidden">
                  <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 1440 320" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="120" cy="40" fill="#b40068" opacity="0.65" r="8"></circle>
                    <circle cx="280" cy="90" fill="#cba900" opacity="0.75" r="5"></circle>
                    <circle cx="450" cy="30" fill="#351078" opacity="0.45" r="10"></circle>
                    <circle cx="680" cy="110" fill="#b40068" opacity="0.5" r="7"></circle>
                    <circle cx="920" cy="50" fill="#1e0051" opacity="0.4" r="9"></circle>
                    <circle cx="1140" cy="95" fill="#cba900" opacity="0.8" r="6"></circle>
                    <circle cx="1320" cy="35" fill="#b40068" opacity="0.6" r="8"></circle>
                    <path d="M40,120 Q120,40 200,100 T360,60" fill="none" opacity="0.4" stroke="#e10084" strokeDasharray="8 6" strokeLinecap="round" strokeWidth="3"></path>
                    <path d="M1020,40 Q1120,120 1240,60 T1400,110" fill="none" opacity="0.5" stroke="#cba900" strokeDasharray="10 6" strokeLinecap="round" strokeWidth="3"></path>
                  </svg>
                </div>

                <div className="relative max-w-[1280px] mx-auto px-margin-mobile lg:px-margin flex flex-col gap-space-md">
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                    <div className="inline-flex items-center gap-2 px-space-sm py-1 rounded-full bg-surface-container-highest shadow-sm">
                      <span className="inline-block w-2.5 h-2.5 rounded-full bg-secondary animate-ping"></span>
                      <span className="font-label-sm text-label-sm text-primary uppercase font-bold tracking-wider">Mama Edi Mana Adda!</span>
                      <span className="text-outline-variant">•</span>
                      <span className="font-label-sm text-label-sm text-on-surface-variant font-medium">Vadlamudi Prime Celebrations</span>
                    </div>
                    <div className="inline-flex items-center gap-2 px-space-sm py-1 rounded-full bg-surface-container text-on-surface-variant shadow-sm">
                      <span className="material-symbols-outlined text-[16px] text-primary">verified_user</span>
                      <span className="font-label-sm text-label-sm font-semibold">Secure Hash Token</span>
                      <span className="hidden sm:inline font-body-sm text-body-sm text-outline">| Private Instant Confirmation</span>
                    </div>
                  </div>

                  {/* State 1: Confirmed Banner */}
                  {activeState === 'confirmed' && (
                    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-space-md p-space-md lg:p-space-lg rounded-lg bg-surface-container-lowest shadow-xl relative overflow-hidden">
                      <div className="absolute -right-8 -top-8 w-44 h-44 rounded-full bg-secondary-fixed/50 blur-3xl pointer-events-none"></div>
                      <div className="flex items-start sm:items-center gap-4 relative z-10">
                        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-primary flex items-center justify-center shrink-0 shadow-lg text-secondary-fixed">
                          <span className="material-symbols-outlined text-[36px] sm:text-[44px]" style={{ fontVariationSettings: "'FILL' 1" }}>celebration</span>
                        </div>
                        <div className="flex flex-col gap-1">
                          <div className="inline-flex items-center gap-2">
                            <span className="px-space-xs py-0.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed font-label-sm text-label-sm font-bold flex items-center gap-1">
                              <span className="material-symbols-outlined text-[14px]">check_circle</span>
                              Slot 100% Reserved & Locked
                            </span>
                            <span className="hidden sm:inline font-label-sm text-label-sm text-secondary font-semibold">Host Kiran Kumar Verified</span>
                          </div>
                          <h1 className="font-headline-lg text-headline-lg-mobile sm:text-headline-lg text-primary tracking-tight font-bold">Party Locked & Confirmed!</h1>
                          <p className="font-body-md text-body-md text-on-surface-variant">The celebration is officially on the calendar. Welcome advance received.</p>
                        </div>
                      </div>
                      <div className="w-full lg:w-auto flex flex-col sm:flex-row lg:flex-col items-start lg:items-end justify-between gap-3 relative z-10 pt-2 lg:pt-0">
                        <div className="flex flex-col lg:items-end bg-surface-container px-space-md py-2.5 rounded-lg w-full sm:w-auto">
                          <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant font-bold">Party Starts In</span>
                          <div className="flex items-center gap-2 font-headline-md text-headline-md text-secondary font-bold">
                            <span>08</span><span className="text-xs text-outline">DAYS</span>:
                            <span>14</span><span className="text-xs text-outline">HRS</span>:
                            <span>32</span><span className="text-xs text-outline">MIN</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5 text-on-surface-variant font-label-sm text-label-sm">
                          <span className="material-symbols-outlined text-[16px] text-tertiary">notifications_active</span>
                          <span>Host Kiran Kumar notified & pre-booking AC at 21°C</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* State 2: Inquiry Received Banner */}
                  {activeState === 'inquiry' && (
                    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-space-md p-space-md lg:p-space-lg rounded-lg bg-surface-container-high shadow-xl relative overflow-hidden">
                      <div className="flex items-start sm:items-center gap-4 relative z-10">
                        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-tertiary-container flex items-center justify-center shrink-0 shadow-lg text-on-tertiary-container">
                          <span className="material-symbols-outlined text-[36px] sm:text-[44px]">history_toggle_off</span>
                        </div>
                        <div className="flex flex-col gap-1">
                          <div className="inline-flex items-center gap-2">
                            <span className="px-space-xs py-0.5 rounded-full bg-surface-container-lowest text-tertiary font-label-sm text-label-sm font-bold flex items-center gap-1 shadow-sm">
                              <span className="material-symbols-outlined text-[14px]">hourglass_top</span>
                              Host Verification Pending
                            </span>
                            <span className="font-label-sm text-label-sm text-primary font-semibold">Zero Payment Charged</span>
                          </div>
                          <h1 className="font-headline-lg text-headline-lg-mobile sm:text-headline-lg text-primary tracking-tight font-bold">Custom Inquiry Received!</h1>
                          <p className="font-body-md text-body-md text-on-surface-variant">The host is reviewing the theme details.</p>
                        </div>
                      </div>
                      <div className="flex flex-col lg:items-end gap-2">
                        <a className="inline-flex items-center gap-2 px-space-md py-2.5 rounded-full bg-primary text-on-primary font-label-md text-label-md shadow-md hover:bg-primary-container transition-all" href={`tel:${VENUE_CONFIG.whatsappNumber}`}>
                          <span className="material-symbols-outlined text-[18px]">phone_in_talk</span>
                          <span>Urgent Slot? Call Kiran Now</span>
                        </a>
                        <span className="font-body-sm text-body-sm text-on-surface-variant">Average host phone callback: &lt; 8 minutes</span>
                      </div>
                    </div>
                  )}

                  {/* State 3: Payment Pending Banner */}
                  {activeState === 'pending' && (
                    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-space-md p-space-md lg:p-space-lg rounded-lg bg-surface-container-lowest shadow-xl relative overflow-hidden">
                      <div className="flex items-start sm:items-center gap-4 relative z-10">
                        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-secondary-container flex items-center justify-center shrink-0 shadow-lg text-on-secondary-container animate-pulse">
                          <span className="material-symbols-outlined text-[36px] sm:text-[44px]">lock_clock</span>
                        </div>
                        <div className="flex flex-col gap-1">
                          <div className="inline-flex items-center gap-2">
                            <span className="px-space-xs py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm font-bold flex items-center gap-1">
                              <span className="material-symbols-outlined text-[14px]">timer</span>
                              Temporary Server Lock Active
                            </span>
                            <span className="font-label-sm text-label-sm text-secondary font-bold">Server Hold Active</span>
                          </div>
                          <h1 className="font-headline-lg text-headline-lg-mobile sm:text-headline-lg text-primary tracking-tight font-bold">Lock this slot</h1>
                          <p className="font-body-md text-body-md text-on-surface-variant">Complete your reservation deposit now to guarantee this 06:00 PM – 08:00 PM prime slot before release to the waitlist.</p>
                        </div>
                      </div>
                      <div className="w-full lg:w-auto flex flex-col sm:flex-row lg:flex-col items-start lg:items-end gap-3">
                        <div className="flex items-center gap-3 bg-secondary-fixed/50 px-space-md py-2.5 rounded-lg">
                          <span className="material-symbols-outlined text-secondary text-[26px]">alarm</span>
                          <div>
                            <span className="font-label-sm text-label-sm text-on-secondary-fixed block">Hold Expires In:</span>
                            <span className="font-headline-md text-headline-md text-secondary font-bold">08:42</span>
                          </div>
                        </div>
                        {payError && (
                          <div className="w-full text-xs text-error font-medium p-2 rounded bg-error-container">
                            {payError}
                          </div>
                        )}
                        {VENUE_CONFIG.paymentsEnabled ? (
                          <button
                            className="w-full sm:w-auto px-space-lg py-3 rounded-full bg-secondary text-on-secondary font-label-lg text-label-lg font-bold shadow-lg hover:bg-secondary-container transition-all flex items-center justify-center gap-2 disabled:bg-surface-container-high disabled:text-on-surface-variant"
                            disabled={paying}
                            onClick={handlePayAdvance}
                          >
                            {paying ? (
                              <>
                                <div className="w-5 h-5 rounded-full border-2 border-on-secondary border-t-transparent animate-spin" />
                                <span>Connecting to Razorpay...</span>
                              </>
                            ) : (
                              <>
                                <span className="material-symbols-outlined text-[20px]">account_balance_wallet</span>
                                <span>Pay Deposit via UPI / Card</span>
                              </>
                            )}
                          </button>
                        ) : (
                          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full">
                            <div className="text-xs text-on-surface-variant p-2.5 rounded bg-surface-container-high border border-outline flex-1">
                              Online payments are deferred. Your slot reservation is held! Please pay the advance directly at the venue (Cash or UPI to Host Kiran Kumar).
                            </div>
                            <a
                              href={`https://wa.me/${VENUE_CONFIG.whatsappNumber}?text=Hi%20Kiran!%20I%20have%20reserved%20Joybox%20(${bookingRef}).%20Please%20confirm%20my%20slot.`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-5 py-2.5 rounded-full bg-[#075E54] text-on-primary font-label-md text-label-md font-bold shadow hover:brightness-110 flex items-center justify-center gap-2"
                            >
                              <span className="material-symbols-outlined text-[18px]">chat</span>
                              <span>WhatsApp Host Kiran</span>
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* State 4: Payment Failed / Expired Banner */}
                  {activeState === 'failed' && (
                    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-space-md p-space-md lg:p-space-lg rounded-lg bg-error-container text-on-error-container shadow-xl relative overflow-hidden">
                      <div className="flex items-start sm:items-center gap-4 relative z-10">
                        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-error flex items-center justify-center shrink-0 shadow-lg text-on-error">
                          <span className="material-symbols-outlined text-[36px] sm:text-[44px]">warning</span>
                        </div>
                        <div className="flex flex-col gap-1">
                          <div className="inline-flex items-center gap-2">
                            <span className="px-space-xs py-0.5 rounded-full bg-surface-container-lowest text-error font-label-sm text-label-sm font-bold flex items-center gap-1 shadow-sm">
                              <span className="material-symbols-outlined text-[14px]">cancel</span>
                              Transaction Interrupted
                            </span>
                            <span className="font-label-sm text-label-sm font-semibold">Courtesy Hold Active</span>
                          </div>
                          <h1 className="font-headline-lg text-headline-lg-mobile sm:text-headline-lg text-on-error-container tracking-tight font-bold">Payment Session Interrupted</h1>
                          <p className="font-body-md text-body-md text-on-error-container/90">The payment session was timed out or declined. This slot is temporarily held so no one else books it.</p>
                        </div>
                      </div>
                      <div className="flex flex-col sm:flex-row lg:flex-col items-stretch sm:items-center lg:items-end gap-2.5 w-full lg:w-auto">
                        <button className="px-space-md py-2.5 rounded-full bg-error text-on-error font-label-md text-label-md font-bold shadow-md hover:opacity-90 transition-all flex items-center justify-center gap-2" onClick={() => handleStateChange('pending')}>
                          <span className="material-symbols-outlined text-[18px]">replay</span>
                          <span>Retry Payment</span>
                        </button>
                        <a className="px-space-md py-2 rounded-full bg-surface-container-lowest text-primary font-label-md text-label-md font-bold shadow-sm flex items-center justify-center gap-2" href={`https://wa.me/${VENUE_CONFIG.whatsappNumber}?text=Hi,%20my%20payment%20failed.%20Please%20hold%20my%20slot.`} target="_blank" rel="noopener noreferrer">
                          <span className="material-symbols-outlined text-[18px] text-[#075E54]">chat</span>
                          <span>WhatsApp Kiran to Hold</span>
                        </a>
                      </div>
                    </div>
                  )}

                  {/* State 5: Cancelled Banner */}
                  {activeState === 'cancelled' && (
                    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-space-md p-space-md lg:p-space-lg rounded-lg bg-surface-container-high text-on-surface shadow-xl relative overflow-hidden border border-outline-variant">
                      <div className="flex items-start sm:items-center gap-4 relative z-10">
                        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-error-container text-error flex items-center justify-center shrink-0 shadow-lg">
                          <span className="material-symbols-outlined text-[36px] sm:text-[44px]">cancel</span>
                        </div>
                        <div className="flex flex-col gap-1">
                          <div className="inline-flex items-center gap-2">
                            <span className="px-space-xs py-0.5 rounded-full bg-error-container text-error font-label-sm text-label-sm font-bold flex items-center gap-1 shadow-sm">
                              <span className="material-symbols-outlined text-[14px]">cancel</span>
                              Reservation Cancelled
                            </span>
                            <span className="font-label-sm text-label-sm font-semibold text-on-surface-variant">Slot Released Back to Public</span>
                          </div>
                          <h1 className="font-headline-lg text-headline-lg-mobile sm:text-headline-lg text-primary tracking-tight font-bold">Booking Has Been Cancelled</h1>
                          <p className="font-body-md text-body-md text-on-surface-variant">
                            {cancelMessage || bookingData?.cancellationReason || 'This booking has been cancelled and the hall slot has been made available for other celebrations.'}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-col sm:flex-row lg:flex-col items-stretch sm:items-center lg:items-end gap-2.5 w-full lg:w-auto">
                        <a className="px-space-md py-2.5 rounded-full bg-primary text-on-primary font-label-md text-label-md font-bold shadow-md hover:opacity-90 transition-all flex items-center justify-center gap-2" href="/book">
                          <span className="material-symbols-outlined text-[18px]">calendar_today</span>
                          <span>Book New Celebration</span>
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              </section>

              {/* Main Booking Details & Financials (Asymmetric Bento Grid) */}
              <section className="w-full py-space-lg">
                <div className="max-w-[1280px] mx-auto px-margin-mobile lg:px-margin flex flex-col gap-space-lg">
                  {/* Booking Hash Identifier Bar */}
                  <div className="p-space-md rounded-lg bg-surface-container-lowest shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-sm">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-secondary-fixed flex items-center justify-center text-on-secondary-fixed">
                        <span className="material-symbols-outlined text-[22px]">confirmation_number</span>
                      </div>
                      <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                          <span className="font-body-sm text-body-sm text-on-surface-variant font-medium">Booking ID:</span>
                          <span className="font-headline-sm text-headline-sm text-primary font-bold tracking-tight">
                            {bookingData?.bookingReference || (bookingRef ? `#${bookingRef}` : '#JBX-VDL-8429-CONF')}
                          </span>
                        </div>
                        <span className="font-label-sm text-label-sm text-secondary">
                          {bookingData?.celebrantName ? `${bookingData.celebrantName}'s Celebration` : 'Your celebration'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 self-stretch sm:self-auto justify-end">
                      {bookingData?.bookingStatus !== 'cancelled' && userToken && (
                        <button
                          className="px-space-md py-2 rounded-full bg-error-container hover:bg-error/20 text-error font-label-md text-label-md font-semibold transition-all flex items-center gap-1.5 shadow-sm active:scale-95 disabled:bg-surface-container-high disabled:text-on-surface-variant"
                          onClick={handleCancelBooking}
                          disabled={cancelling}
                        >
                          <span className="material-symbols-outlined text-[18px]">cancel</span>
                          <span>{cancelling ? 'Cancelling...' : 'Cancel Reservation'}</span>
                        </button>
                      )}
                      <button className="px-space-md py-2 rounded-full bg-surface-container hover:bg-surface-container-high text-primary font-label-md text-label-md font-semibold transition-all flex items-center gap-1.5 shadow-sm active:scale-95" onClick={copyBookingRef}>
                        <span className="material-symbols-outlined text-[18px]">content_copy</span>
                        <span>{copied ? 'Copied!' : 'Copy Code'}</span>
                      </button>
                      <button className="px-space-sm py-2 rounded-full bg-surface-container hover:bg-surface-container-high text-primary font-label-md text-label-md font-semibold transition-all flex items-center gap-1.5 shadow-sm" onClick={() => window.print()}>
                        <span className="material-symbols-outlined text-[18px]">receipt_long</span>
                        <span className="hidden sm:inline">Print Receipt</span>
                      </button>
                    </div>
                  </div>

                  {/* Bento Grid Breakdown */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-md lg:gap-space-lg">
                    {/* Left Column: Particulars (7 Cols) */}
                    <div className="lg:col-span-7 flex flex-col gap-space-md">
                      <div className="p-space-lg rounded-lg bg-surface-container-lowest shadow-md flex flex-col gap-space-md">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-secondary text-[24px]">event</span>
                            <span className="font-title-lg text-title-lg text-primary font-bold">Celebration Timing &amp; Venue Slot</span>
                          </div>
                          <span className="px-space-xs py-0.5 rounded-full bg-surface-container-high text-primary font-label-sm text-label-sm font-bold">Private Theater Buyout</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                          <div className="p-space-sm rounded-lg bg-surface-container-low flex flex-col gap-1">
                            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-bold">Party Date</span>
                            <span className="font-headline-sm text-headline-sm text-primary font-bold">Saturday, Oct 25, 2024</span>
                            <span className="font-body-sm text-body-sm text-secondary font-medium">Weekend Evening Prime Slot</span>
                          </div>
                          <div className="p-space-sm rounded-lg bg-surface-container-low flex flex-col gap-1">
                            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-bold">Reserved Hours</span>
                            <span className="font-headline-sm text-headline-sm text-primary font-bold">06:00 PM – 08:00 PM</span>
                            <span className="font-body-sm text-body-sm text-tertiary font-bold">+15 Min Free Early Setup (05:45 PM Entry)</span>
                          </div>
                        </div>
                        <div className="p-space-sm rounded-lg bg-surface-container flex items-center justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <div className="w-11 h-11 rounded-full bg-primary text-on-primary flex items-center justify-center font-bold text-lg">K</div>
                            <div className="flex flex-col">
                              <span className="font-label-sm text-label-sm text-on-surface-variant font-medium">Dedicated On-Site Host</span>
                              <span className="font-headline-sm text-base text-primary font-bold">Kiran Kumar</span>
                              <span className="font-body-sm text-xs text-on-surface-variant">Personalized setup &amp; guest assistance</span>
                            </div>
                          </div>
                          <a className="px-space-md py-1.5 rounded-full bg-surface-container-lowest text-primary hover:bg-surface-container-high transition-colors font-label-sm text-label-sm font-semibold flex items-center gap-1 shadow-sm" href={`tel:${VENUE_CONFIG.whatsappNumber}`}>
                            <span className="material-symbols-outlined text-[16px] text-secondary">call</span>
                            <span>Call Kiran</span>
                          </a>
                        </div>
                      </div>

                      <div className="p-space-lg rounded-lg bg-surface-container-lowest shadow-md flex flex-col gap-space-md">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-secondary text-[24px]">inventory_2</span>
                            <span className="font-title-lg text-title-lg text-primary font-bold">Locked Package Particulars</span>
                          </div>
                          <span className="px-space-xs py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm font-bold">Gold Gala Tier</span>
                        </div>
                        <div className="flex flex-col gap-2.5 pt-1 font-body-md text-body-md text-on-surface">
                          <div className="flex items-start gap-2.5">
                            <span className="material-symbols-outlined text-secondary text-[20px] mt-0.5">cake</span>
                            <p><strong>Designer cake:</strong> Shown here only as a layout sample. The live booking uses the package the host configures.</p>
                          </div>
                          <div className="flex items-start gap-2.5">
                            <span className="material-symbols-outlined text-secondary text-[20px] mt-0.5">stars</span>
                            <p><strong>Personalized Neon Name Board:</strong> "AARADHYA" lit in pink neon against a rainbow backdrop.</p>
                          </div>
                          <div className="flex items-start gap-2.5">
                            <span className="material-symbols-outlined text-secondary text-[20px] mt-0.5">ac_unit</span>
                            <p><strong>Private Climate Controlled Hall:</strong> Chilled to 21°C with JBL sound system &amp; wireless mics.</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Right Column: Financials & Policy (5 Cols) */}
                    <div className="lg:col-span-5 flex flex-col gap-space-md">
                      <div className="p-space-lg rounded-lg bg-surface-container-lowest shadow-md flex flex-col gap-space-md">
                        <div className="flex items-center justify-between border-b border-outline pb-space-sm">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-secondary text-[24px]">receipt</span>
                            <span className="font-title-lg text-title-lg text-primary font-bold">Payment Breakdown</span>
                          </div>
                          <span className="px-space-xs py-0.5 rounded-full bg-surface-container text-on-surface-variant font-label-sm text-label-sm font-semibold">INR (₹)</span>
                        </div>

                        <div className="flex flex-col gap-2 text-body-md text-on-surface-variant">
                          <div className="flex justify-between">
                            <span>Gold Tier (2 hrs × ₹1,500/hr)</span>
                            <span className="font-semibold text-on-surface">₹3,000</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Low-Lying Fog Cloud Entry</span>
                            <span className="font-semibold text-on-surface">₹500</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Bubble Machine Entry</span>
                            <span className="font-semibold text-on-surface">₹300</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Cold Fire Spark Blasts (2 shots)</span>
                            <span className="font-semibold text-on-surface">₹600</span>
                          </div>
                          <div className="flex justify-between text-tertiary font-medium">
                            <span>Promotion</span>
                            <span>- ₹300</span>
                          </div>
                          <div className="flex justify-between pt-2 border-t border-outline font-bold text-primary text-lg">
                            <span>Total Package Bill</span>
                            <span className="text-secondary">₹4,100</span>
                          </div>
                          <div className="flex justify-between pt-1 font-semibold text-primary">
                            <span>Advance Paid Online</span>
                            <span className="text-tertiary">Verified</span>
                          </div>
                          <div className="flex justify-between pt-2 border-t border-outline text-headline-sm font-extrabold text-primary">
                            <span>Balance Due at Venue</span>
                            <span className="text-secondary">₹3,600</span>
                          </div>
                        </div>
                      </div>

                      <div className="p-space-md rounded-lg bg-surface-container-low shadow-sm flex flex-col gap-2">
                        <span className="font-title-lg text-base text-primary font-bold flex items-center gap-1.5">
                          <span className="material-symbols-outlined text-secondary text-[20px]">policy</span>
                          <span>Venue Policy Reminders</span>
                        </span>
                        <ul className="text-xs text-on-surface-variant flex flex-col gap-1.5 list-disc pl-4">
                          <li>External food/catering is welcome. Sterno heaters or gas cylinders not permitted.</li>
                          <li>Outside shoes strictly removed at entrance shoe rack.</li>
                          <li>Cancellation eligible for refund based on time before event. Host: Kiran Kumar.</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            </>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
