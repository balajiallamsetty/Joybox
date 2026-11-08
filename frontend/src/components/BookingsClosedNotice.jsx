import React from 'react';
import { useLanguage } from './LanguageContext';

export default function BookingsClosedNotice({ whatsappNumber = '917842704429' }) {
  const { lang } = useLanguage();
  const cleanNumber = (whatsappNumber || '917842704429').replace(/\D/g, '') || '917842704429';

  const isTe = lang === 'te';
  const heading = isTe ? 'ఆన్‌లైన్ బుకింగ్‌లు ప్రస్తుతానికి మూసివేయబడ్డాయి' : 'Online Bookings Are Currently Closed';
  const message = isTe
    ? 'మీరు మా వేదిక ప్యాకేజీలు, అదనపు సేవలు మరియు అందుబాటులో ఉన్న సమయాలను కింద చూడవచ్చు! మీ వేడుకను బుక్ చేసుకోవడానికి లేదా వివరాల కొరకు నేరుగా మా హోస్ట్‌ను వాట్సాప్‌లో సంప్రదించండి.'
    : 'You can still browse party packages, add-ons, and real-time availability below! To reserve your party or hold a custom slot, message our host directly on WhatsApp.';
  const waCta = isTe ? 'వాట్సాప్‌లో సంప్రదించండి' : 'Inquire via WhatsApp';
  const waPrefill = encodeURIComponent(
    isTe
      ? 'నమస్కారం జాయ్‌బాక్స్! నేను వడ్లమూడి పార్టీ రూమ్ బుకింగ్ గురించి వివరాలు తెలుసుకోవాలనుకుంటున్నాను.'
      : 'Hi Joybox! I would like to inquire about booking the party room in Vadlamudi.'
  );

  return (
    <div
      role="status"
      aria-live="polite"
      tabIndex={-1}
      data-testid="bookings-closed-notice"
      className="w-full my-4 p-5 sm:p-6 rounded-2xl bg-amber-500/10 border-2 border-amber-500/30 text-amber-950 dark:text-amber-100 shadow-md backdrop-blur-sm transition-all animate-fade-in"
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-700 dark:text-amber-300 flex items-center justify-center shrink-0 mt-0.5">
            <span className="material-symbols-outlined text-[24px]">campaign</span>
          </div>
          <div>
            <h3 className="font-title-md text-title-md font-bold text-amber-900 dark:text-amber-200 mb-1">
              {heading}
            </h3>
            <p className="font-body-md text-body-md text-amber-900/90 dark:text-amber-100/90 max-w-2xl leading-relaxed">
              {message}
            </p>
          </div>
        </div>

        <a
          href={`https://wa.me/${cleanNumber}?text=${waPrefill}`}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="bookings-closed-wa-btn"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#075E54] hover:bg-[#064e46] text-white font-label-md text-label-md shadow-md hover:shadow-lg transition-all shrink-0 active:scale-95"
        >
          <span className="material-symbols-outlined text-[20px]">chat</span>
          <span>{waCta}</span>
        </a>
      </div>
    </div>
  );
}
