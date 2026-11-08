import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import BookingsClosedNotice from '../components/BookingsClosedNotice';
import { useLanguage } from '../components/LanguageContext';
import { api } from '../services/api';

export default function AddonsPage() {
  const { lang } = useLanguage();
  const isTe = lang === 'te';

  const [addons, setAddons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [publicConfig, setPublicConfig] = useState(null);

  const fetchAddonsData = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.getAddOns(),
      api.getPublicConfig().catch(() => ({ data: { bookingsOpen: true, whatsappNumber: '917842704429' } })),
    ])
      .then(([addonRes, configRes]) => {
        setAddons(addonRes?.items || []);
        setPublicConfig(configRes?.data || configRes || {});
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load celebration add-ons.');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchAddonsData();
  }, []);

  const bookingsOpen = publicConfig?.bookingsOpen ?? true;
  const waNumber = publicConfig?.whatsappNumber || '917842704429';

  return (
    <div className="w-full min-h-screen bg-background">
      <Header />
      <main className="w-full pt-20 bg-background">
        <div className="flex flex-col w-full">
          {/* Hero Banner */}
          <div className="w-full relative overflow-hidden bg-surface-container-low py-space-xl px-gutter">
            <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-[720px] h-72 bg-gradient-to-r from-secondary/15 via-tertiary-fixed/25 to-primary/10 blur-3xl pointer-events-none rounded-full" />
            <div className="max-w-7xl mx-auto flex flex-col items-center text-center relative z-10">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-surface-container-highest/80 backdrop-blur-md shadow-sm mb-4">
                <span className="w-2 h-2 rounded-full bg-secondary animate-ping" />
                <span className="font-label-sm text-label-sm tracking-widest text-primary uppercase">
                  {isTe ? 'అదనపు వేడుక సేవలు' : 'Celebration Upgrades & Add-ons'}
                </span>
              </div>
              <h1 className="font-display-hero text-display-hero text-primary max-w-4xl tracking-tight mb-4">
                {isTe ? 'మీ వేడుకను మరింత ఘనంగా మార్చుకోండి' : 'Make Every Moment Extraordinary'}
              </h1>
              <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl leading-relaxed mb-4">
                {isTe
                  ? 'జాయ్‌బాక్స్ వద్ద బబుల్ ఎంట్రీ, స్మోక్/ఫాగ్ ఎఫెక్ట్స్, కోల్డ్-ఫైర్ స్పార్క్స్ వంటి అద్భుతమైన స్పెషల్ ఎఫెక్ట్స్‌తో మీ కేక్ కట్టింగ్ మరియు ఎంట్రీలను మరపురాని జ్ఞాపకంగా మార్చుకోండి.'
                  : 'Upgrade your party with magical bubble entries, dense royal fog clouds, and indoor cold-fire pyrotechnic spark blasts. Safe, exciting, and unforgettable.'}
              </p>
            </div>
          </div>

          {/* Main Content Area */}
          <section className="w-full py-space-xl bg-background">
            <div className="max-w-7xl mx-auto px-gutter flex flex-col gap-8">
              {!bookingsOpen && (
                <BookingsClosedNotice whatsappNumber={waNumber} />
              )}

              {loading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4" data-testid="addons-loading">
                  <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-secondary border-t-transparent" />
                  <p className="font-label-md text-label-md text-on-surface-variant animate-pulse">
                    {isTe ? 'అదనపు సేవలను లోడ్ చేస్తున్నాము...' : 'Loading celebration add-ons...'}
                  </p>
                </div>
              ) : error ? (
                <div className="max-w-xl mx-auto p-6 rounded-2xl bg-error-container text-on-error-container shadow-md text-center flex flex-col items-center gap-4">
                  <span className="material-symbols-outlined text-4xl text-error">error</span>
                  <div>
                    <h3 className="font-title-lg text-title-lg font-bold mb-1">
                      {isTe ? 'సేవలను లోడ్ చేయలేకపోయాము' : 'Could Not Load Add-ons'}
                    </h3>
                    <p className="font-body-sm text-body-sm opacity-90">{error}</p>
                  </div>
                  <button
                    onClick={fetchAddonsData}
                    className="px-6 py-2.5 rounded-full bg-secondary text-on-secondary font-label-md hover:bg-secondary-container transition-all shadow"
                  >
                    {isTe ? 'మళ్ళీ ప్రయత్నించండి' : 'Retry'}
                  </button>
                </div>
              ) : addons.length === 0 ? (
                <div className="text-center py-16 bg-surface-container-low rounded-3xl p-8 max-w-lg mx-auto">
                  <span className="material-symbols-outlined text-5xl text-outline mb-2">stars</span>
                  <h3 className="font-title-lg text-title-lg font-bold text-primary mb-2">
                    {isTe ? 'అదనపు సేవలు అందుబాటులో లేవు' : 'No Add-ons Available'}
                  </h3>
                  <p className="font-body-md text-body-md text-on-surface-variant mb-6">
                    {isTe ? 'త్వరలోనే కొత్త సేవలు జోడించబడతాయి.' : 'Exciting celebration add-ons will be listed here soon.'}
                  </p>
                  <Link
                    to="/packages"
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-secondary text-on-secondary font-label-md font-bold"
                  >
                    <span>{isTe ? 'ప్యాకేజీలను చూడండి' : 'View Packages'}</span>
                  </Link>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="addons-grid">
                  {addons.map((addon) => {
                    const priceInRupees = (addon.priceMinor || 0) / 100;
                    const formattedPrice = `₹${priceInRupees.toLocaleString('en-IN')}`;
                    const title = isTe && addon.nameTe ? addon.nameTe : addon.name;
                    const desc = isTe && addon.descriptionTe ? addon.descriptionTe : addon.description;
                    const icon = addon.iconSymbol || 'celebration';

                    return (
                      <div
                        key={addon.code}
                        data-testid={`addon-card-${addon.code}`}
                        className="flex flex-col justify-between p-6 rounded-3xl bg-surface-container-lowest border border-outline/30 shadow-sm hover:shadow-lg transition-all duration-300 group hover:-translate-y-1"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-4 mb-4">
                            <div className="w-14 h-14 rounded-2xl bg-secondary/10 text-secondary flex items-center justify-center group-hover:scale-110 transition-transform">
                              <span className="material-symbols-outlined text-[32px]">{icon}</span>
                            </div>
                            <span className="font-title-lg text-title-lg font-bold text-primary">
                              {formattedPrice}
                            </span>
                          </div>

                          <h3 className="font-title-lg text-title-lg font-bold text-primary mb-2">
                            {title}
                          </h3>
                          <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed mb-6">
                            {desc}
                          </p>
                        </div>

                        <div className="pt-4 border-t border-outline/20 flex flex-col gap-2">
                          <Link
                            to={`/booking?addons=${encodeURIComponent(addon.code)}`}
                            className="w-full py-3 px-4 rounded-full bg-secondary hover:bg-secondary-container text-on-secondary hover:text-on-secondary-container font-label-md font-bold text-center transition-all shadow-sm active:scale-95 flex items-center justify-center gap-2"
                          >
                            <span className="material-symbols-outlined text-[18px]">add_circle</span>
                            <span>{isTe ? 'ఈ సేవతో బుక్ చేయండి' : 'Book With This Add-on'}</span>
                          </Link>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
