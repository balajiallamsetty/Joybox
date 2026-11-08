import React from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';

export default function RefundPolicyPage() {
  return (
    <div className="w-full min-h-screen bg-background">
      <Header />
      <main className="w-full pt-20 pb-16 bg-background">
        <div className="max-w-4xl mx-auto px-gutter">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-high text-xs font-bold text-secondary uppercase mb-4">
            <span>Transparent Guarantee</span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-primary mb-2">Cancellation &amp; Refund Policy</h1>
          <p className="text-on-surface-variant text-sm mb-6">
            Clear, Fair Cancellation Rules • Joybox Party Room (Vadlamudi, Guntur)
          </p>

          <div className="p-4 mb-6 rounded-xl bg-tertiary-fixed border border-tertiary text-on-tertiary-fixed text-xs flex items-start gap-2">
            <span className="material-symbols-outlined text-base mt-0.5">info</span>
            <div>
              <span className="font-bold uppercase tracking-wider block">Owner Review Placeholder Notice</span>
              <span>This cancellation draft contains proposed refund windows and tiers for Joybox Party Room. Host Kiran Kumar must review, confirm cancellation fees, and approve before production launch.</span>
            </div>
          </div>

          <div className="space-y-6 text-on-surface text-sm leading-relaxed">
            {/* Refund Tiers Table */}
            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">1. Refund Tiers &amp; Notice Windows</h2>
              <p className="mb-4">
                Because Joybox guarantees 100% private hall access and reserves high-clarity AV systems, customized signage, and decor exclusively for your event, cancellations are subject to advance notice tiers:
              </p>

              <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Cancellation policy refund percentages">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-outline text-primary font-bold">
                      <th className="py-3 px-4">Cancellation Notice Window</th>
                      <th className="py-3 px-4">Refund Percentage</th>
                      <th className="py-3 px-4">Processing Timeline</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/20">
                    <tr>
                      <td className="py-3 px-4 font-semibold text-primary">More than 48 Hours before Start</td>
                      <td className="py-3 px-4 text-emerald-800 font-bold">100% Full Refund</td>
                      <td className="py-3 px-4 text-on-surface-variant">5–7 business days to original source</td>
                    </tr>
                    <tr>
                      <td className="py-3 px-4 font-semibold text-primary">Between 24 and 48 Hours before Start</td>
                      <td className="py-3 px-4 text-amber-800 font-bold">50% Partial Refund</td>
                      <td className="py-3 px-4 text-on-surface-variant">5–7 business days to original source</td>
                    </tr>
                    <tr>
                      <td className="py-3 px-4 font-semibold text-primary">Less than 24 Hours before Start</td>
                      <td className="py-3 px-4 text-rose-700 font-bold">0% Non-Refundable</td>
                      <td className="py-3 px-4 text-on-surface-variant">N/A (Hall locked for your slot)</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <p className="mt-4 text-xs text-secondary font-semibold">
                [OWNER TO APPROVE] In case of emergency or unexpected circumstances, Host Kiran Kumar may permit 1 free date/slot reschedule subject to venue availability.
              </p>
            </section>

            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">2. How to Request Cancellation</h2>
              <p>
                To request a cancellation or reschedule, contact Host Kiran Kumar with your booking reference ID:
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <a
                  href="https://wa.me/917842704429?text=Hi%20Joybox!%20I%20need%20to%20request%20a%20booking%20cancellation%20or%20reschedule."
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-6 py-2.5 rounded-full bg-[#075E54] text-on-primary font-label-md flex items-center gap-2 hover:brightness-110 shadow-sm"
                >
                  <span className="material-symbols-outlined text-base">chat</span>
                  <span>WhatsApp Host (+91 78427 04429)</span>
                </a>
                <Link
                  to="/booking-status"
                  className="px-6 py-2.5 rounded-full bg-surface-container-high text-primary font-label-md hover:bg-surface-container-highest transition-all"
                >
                  Lookup Booking Online
                </Link>
              </div>
            </section>

            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">3. Mode of Refund</h2>
              <p>
                Refunds are credited back directly to the original payment method used during checkout (UPI VPA, bank account, or credit/debit card) via the Razorpay payment gateway within 5 to 7 business days, in compliance with Reserve Bank of India (RBI) turnaround guidelines.
              </p>
            </section>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

