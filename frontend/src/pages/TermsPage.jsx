import React from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';

export default function TermsPage() {
  return (
    <div className="w-full min-h-screen bg-background">
      <Header />
      <main className="w-full pt-20 pb-16 bg-background">
        <div className="max-w-4xl mx-auto px-gutter">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-high text-xs font-bold text-secondary uppercase mb-4">
            <span>Customer Agreement</span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-primary mb-2">Terms and Conditions</h1>
          <p className="text-on-surface-variant text-sm mb-6">
            Last Updated: October 2026 • Joybox Party Room (Beside Durga Mart, Vadlamudi, Guntur)
          </p>

          <div className="p-4 mb-6 rounded-xl bg-tertiary-fixed border border-tertiary text-on-tertiary-fixed text-xs flex items-start gap-2">
            <span className="material-symbols-outlined text-base mt-0.5">info</span>
            <div>
              <span className="font-bold uppercase tracking-wider block">Owner Review Placeholder Notice</span>
              <span>This policy draft contains operational defaults for Joybox Party Room. Host Kiran Kumar must review, update legal terms, and approve before production launch.</span>
            </div>
          </div>

          <div className="space-y-6 text-on-surface text-sm leading-relaxed">
            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">1. Scope and Booking Policy</h2>
              <p>
                Joybox Party Room provides private, air-conditioned party hall facilities on an hourly reservation model. By making a reservation through our website, mobile interface, or WhatsApp concierge, you agree to comply with all terms set forth herein.
              </p>
              <p className="mt-2 text-xs text-secondary font-semibold">
                [OWNER TO APPROVE] Booking start times must align with the top of the hour. A 30-minute cleaning and sanitization buffer is automatically scheduled between all parties.
              </p>
            </section>

            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">2. Hall Conduct &amp; Outside Catering</h2>
              <p>
                Guests are welcome to bring outside food, snacks, and non-alcoholic beverages without additional cleaning fees. The host provides dedicated tables for food and gifts.
              </p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-on-surface-variant">
                <li>Smoking, alcoholic beverages, and hazardous materials are strictly prohibited on the premises.</li>
                <li>Guests must treat audio-visual, lighting, and projector equipment with care.</li>
                <li>Celebrants are requested to vacate the hall promptly at the conclusion of their reserved time slot to respect subsequent bookings.</li>
              </ul>
            </section>

            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">3. Cancellations, Rescheduling &amp; Refunds</h2>
              <p>
                All cancellation requests are governed by our dedicated{' '}
                <Link to="/refund-policy" className="text-secondary font-bold hover:underline">
                  Cancellation &amp; Refund Policy
                </Link>
                . Cancellations made more than 48 hours prior to start time are eligible for a 100% refund.
              </p>
              <p className="mt-2 text-xs text-secondary font-semibold">
                [OWNER TO APPROVE] Rescheduling requests are subject to slot availability and host Kiran Kumar's approval.
              </p>
            </section>

            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">4. Limitation of Liability</h2>
              <p>
                Joybox Party Room and its operators are not liable for loss or damage to personal belongings brought onto the premises. Celebrants assume responsibility for guest safety during the celebration.
              </p>
            </section>

            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">5. Contact Information</h2>
              <p>
                For questions regarding bookings, policies, or special requests:
              </p>
              <p className="mt-2 font-medium text-primary">
                Host Kiran Kumar • Joybox Party Room<br />
                Beside Durga Mart, Vadlamudi, Guntur, Andhra Pradesh 522213<br />
                WhatsApp / Phone: +91 78427 04429
              </p>
            </section>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

