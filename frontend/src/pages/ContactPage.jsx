import React, { useState } from 'react';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { api } from '../services/api';

export default function ContactPage() {
  const [form, setForm] = useState({
    name: '',
    phone: '',
    preferredDate: '',
    packageCode: 'basic',
    durationHours: 2,
    message: ''
  });
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.createInquiry(form);
      setSent(true);
    } catch (err) {
      setError(err.message || 'Could not send inquiry. Please contact us on WhatsApp.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full min-h-screen bg-background">
      <Header />
      <main className="w-full pt-20 bg-background">
        <div className="flex flex-col w-full">
          {/* Header Banner */}
          <section className="relative w-full max-w-7xl mx-auto px-gutter pt-8 pb-10">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm shadow-sm">
                <span className="material-symbols-outlined text-sm text-secondary">distance</span>
                <span>10 Mins from Vignan's University • Guntur-Tenali Highway</span>
              </div>
              <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-surface-container-high text-primary font-label-sm text-label-sm">
                <span className="material-symbols-outlined text-xs text-tertiary">celebration</span>
                <span>మామ ఇది మన అడ్డా!</span>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-end">
              <div className="lg:col-span-8 flex flex-col gap-3">
                <h1 className="font-display-hero text-headline-lg lg:text-display-hero text-primary tracking-tight">
                  Visit Joybox or Connect With Host <span className="text-secondary italic">Kiran Kumar</span>
                </h1>
                <p className="font-body-lg text-body-lg text-on-surface-variant max-w-3xl">
                  Planning a private birthday surprise, milestone anniversary, romantic movie screening, or college reunion adda? We are right beside Durga Mart on the Vadlamudi Main Road. Reach out anytime — we reply in under 15 minutes!
                </p>
              </div>

              <div className="lg:col-span-4 flex flex-col gap-3">
                <div className="flex items-center gap-3 p-3.5 rounded-lg bg-surface-container-lowest shadow-md">
                  <div className="w-10 h-10 rounded-full bg-primary-container text-on-primary flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-xl text-tertiary-fixed">schedule</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Party Hall Timing</span>
                    <span className="font-title-lg text-title-lg text-primary font-bold">9:00 AM – 10:00 PM</span>
                    <span className="font-body-sm text-body-sm text-secondary font-medium">All 7 Days Open (Daily Sanitized)</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Quick Contact Cards */}
          <section className="relative w-full max-w-7xl mx-auto px-gutter pb-12">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="rounded-lg p-6 bg-surface-container-lowest shadow-md flex flex-col justify-between">
                <div>
                  <div className="w-12 h-12 rounded-full bg-primary-container text-on-primary flex items-center justify-center mb-4">
                    <span className="material-symbols-outlined text-2xl">call</span>
                  </div>
                  <h3 className="font-headline-sm text-headline-sm text-primary mb-1">Direct Phone</h3>
                  <p className="text-sm text-on-surface-variant mb-4">Direct concierge line for availability and quick slot bookings.</p>
                </div>
                <a href="tel:+917842704429" className="font-bold text-secondary text-lg hover:underline">
                  +91 78427 04429
                </a>
              </div>

              <div className="rounded-lg p-6 bg-surface-container-lowest shadow-md flex flex-col justify-between">
                <div>
                  <div className="w-12 h-12 rounded-full bg-[#075E54] text-on-primary flex items-center justify-center mb-4">
                    <span className="material-symbols-outlined text-2xl">chat</span>
                  </div>
                  <h3 className="font-headline-sm text-headline-sm text-primary mb-1">WhatsApp Chat</h3>
                  <p className="text-sm text-on-surface-variant mb-4">Fastest response! Send theme requests, guest counts, and special touches.</p>
                </div>
                <a
                  href="https://wa.me/917842704429?text=Hi%20Kiran!%20I%20want%20to%20enquire%20about%20Joybox%20Party%20Room%20in%20Vadlamudi."
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-bold text-[#075E54] text-lg hover:underline"
                >
                  Chat with Kiran Kumar →
                </a>
              </div>

              <div className="rounded-lg p-6 bg-surface-container-lowest shadow-md flex flex-col justify-between">
                <div>
                  <div className="w-12 h-12 rounded-full bg-secondary text-on-secondary flex items-center justify-center mb-4">
                    <span className="material-symbols-outlined text-2xl">location_on</span>
                  </div>
                  <h3 className="font-headline-sm text-headline-sm text-primary mb-1">Physical Venue</h3>
                  <p className="text-sm text-on-surface-variant mb-4">Beside Durga Mart, Main Road, Vadlamudi, Guntur District, AP.</p>
                </div>
                <span className="font-bold text-primary text-sm">Open Daily: 9 AM - 10 PM</span>
              </div>
            </div>
          </section>

          {/* Inquiry Form */}
          <section className="w-full max-w-4xl mx-auto px-gutter pb-16">
            <div className="p-space-lg rounded-2xl bg-surface-container-lowest shadow-xl border border-outline">
              <h2 className="font-headline-md text-headline-md text-primary mb-2">Send a Direct Celebration Inquiry</h2>
              <p className="text-sm text-on-surface-variant mb-6">Our host Kiran Kumar reviews requests and confirms slots promptly.</p>

              {sent ? (
                <div className="p-6 rounded-xl bg-surface-container-low text-center">
                  <span className="material-symbols-outlined text-4xl text-secondary mb-2">check_circle</span>
                  <h3 className="font-headline-sm text-headline-sm text-primary">Inquiry Sent Successfully!</h3>
                  <p className="text-sm text-on-surface-variant mt-1">Thank you. Kiran Kumar will get in touch with you shortly.</p>
                  <button onClick={() => setSent(false)} className="mt-4 px-6 py-2 rounded-full bg-secondary text-on-secondary text-sm">
                    Send another inquiry
                  </button>
                </div>
              ) : (
                <form onSubmit={submit} className="flex flex-col gap-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="contact-name" className="block text-xs font-bold text-on-surface-variant uppercase mb-1">Your Name *</label>
                      <input
                        id="contact-name"
                        required
                        type="text"
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        placeholder="e.g. Ramesh"
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest"
                      />
                    </div>
                    <div>
                      <label htmlFor="contact-phone" className="block text-xs font-bold text-on-surface-variant uppercase mb-1">Mobile / WhatsApp Number *</label>
                      <input
                        id="contact-phone"
                        required
                        type="tel"
                        value={form.phone}
                        onChange={(e) => setForm({ ...form, phone: e.target.value })}
                        placeholder="e.g. 9876543210"
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label htmlFor="contact-date" className="block text-xs font-bold text-on-surface-variant uppercase mb-1">Preferred Date</label>
                      <input
                        id="contact-date"
                        type="date"
                        value={form.preferredDate}
                        onChange={(e) => setForm({ ...form, preferredDate: e.target.value })}
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest"
                      />
                    </div>
                    <div>
                      <label htmlFor="contact-package" className="block text-xs font-bold text-on-surface-variant uppercase mb-1">Package Tier</label>
                      <select
                        id="contact-package"
                        value={form.packageCode}
                        onChange={(e) => setForm({ ...form, packageCode: e.target.value })}
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest"
                      >
                        <option value="basic">Basic (₹999/hr)</option>
                        <option value="gold">Gold (₹1,500/hr)</option>
                        <option value="diamond">Diamond (₹2,500/hr)</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="contact-duration" className="block text-xs font-bold text-on-surface-variant uppercase mb-1">Duration (Hours)</label>
                      <select
                        id="contact-duration"
                        value={form.durationHours}
                        onChange={(e) => setForm({ ...form, durationHours: Number(e.target.value) })}
                        className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest"
                      >
                        {[1, 2, 3, 4, 5, 6].map((h) => (
                          <option key={h} value={h}>{h} Hour{h > 1 ? 's' : ''}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label htmlFor="contact-message" className="block text-xs font-bold text-on-surface-variant uppercase mb-1">Special Notes / Occasion</label>
                    <textarea
                      id="contact-message"
                      rows="3"
                      value={form.message}
                      onChange={(e) => setForm({ ...form, message: e.target.value })}
                      placeholder="e.g. Surprise 25th anniversary celebration with custom neon signage"
                      className="w-full p-3 rounded-lg border border-outline-variant bg-surface-container-lowest"
                    />
                  </div>

                  {error && <p className="text-sm text-error">{error}</p>}

                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      disabled={loading}
                      className="px-8 py-3.5 rounded-full bg-secondary text-on-secondary font-label-md text-label-md shadow-md hover:bg-secondary-container"
                    >
                      {loading ? 'Submitting...' : 'Submit Celebration Inquiry'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}

