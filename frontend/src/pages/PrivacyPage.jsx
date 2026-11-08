import React from 'react';
import Header from '../components/Header';
import Footer from '../components/Footer';

export default function PrivacyPage() {
  return (
    <div className="w-full min-h-screen bg-background">
      <Header />
      <main className="w-full pt-20 pb-16 bg-background">
        <div className="max-w-4xl mx-auto px-gutter">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-high text-xs font-bold text-secondary uppercase mb-4">
            <span>Customer Privacy</span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-primary mb-2">Privacy Policy</h1>
          <p className="text-on-surface-variant text-sm mb-6">
            Last Updated: October 2026 • Joybox Party Room (Vadlamudi, Guntur)
          </p>

          <div className="p-4 mb-6 rounded-xl bg-tertiary-fixed border border-tertiary text-on-tertiary-fixed text-xs flex items-start gap-2">
            <span className="material-symbols-outlined text-base mt-0.5">info</span>
            <div>
              <span className="font-bold uppercase tracking-wider block">Owner Review Placeholder Notice</span>
              <span>This privacy draft contains recommended data privacy terms for Joybox Party Room. Host Kiran Kumar must review, update legal terms, and approve before production launch.</span>
            </div>
          </div>

          <div className="space-y-6 text-on-surface text-sm leading-relaxed">
            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">1. Information We Collect</h2>
              <p>
                When you initiate a reservation or inquiry at Joybox Party Room, we collect only information strictly necessary to coordinate your celebration:
              </p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-on-surface-variant">
                <li><strong>Contact Phone / WhatsApp Number:</strong> To deliver instant booking confirmations, gate access, and coordinate with Host Kiran Kumar.</li>
                <li><strong>Customer &amp; Celebrant Name:</strong> Displayed on the custom digital name board, welcome easel, and reservation voucher.</li>
                <li><strong>Occasion Details:</strong> Selected celebration package, duration, requested date, and party theme.</li>
              </ul>
            </section>

            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">2. Payment Processing</h2>
              <p>
                All online payments are processed securely through <strong>Razorpay</strong> via PCI-DSS compliant checkout. Joybox Party Room does NOT store your credit card numbers, debit card PINs, CVVs, or net banking credentials on our servers.
              </p>
              <p className="mt-2 text-xs text-secondary font-semibold">
                [OWNER TO APPROVE] Payment transaction IDs and status are retained solely for booking reconciliation, invoice generation, and refunds.
              </p>
            </section>

            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">3. Data Sharing &amp; Third Parties</h2>
              <p>
                We do not sell, rent, or trade your personal information to third-party advertisers. Information is only shared with trusted service providers strictly necessary to operate our service (e.g., Razorpay for payment processing and WhatsApp/SMS gateway providers for booking notices).
              </p>
            </section>

            <section className="p-6 rounded-2xl bg-surface-container-low border border-outline">
              <h2 className="font-title-lg text-title-lg text-primary font-bold mb-3">4. Your Data Rights</h2>
              <p>
                You have the right to request access to your booking records or request deletion of past party inquiries once completed. Contact Host Kiran Kumar on WhatsApp (+91 78427 04429) for assistance.
              </p>
            </section>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

