import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { api } from '../services/api';
import { useLanguage } from '../components/LanguageContext';

export default function GalleryPage() {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [remoteItems, setRemoteItems] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const { isTe } = useLanguage();

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setHasError(false);
    api.getGallery(selectedCategory)
      .then((res) => {
        if (isMounted) {
          if (res?.items && Array.isArray(res.items)) {
            setRemoteItems(res.items);
          } else {
            setRemoteItems([]);
          }
        }
      })
      .catch((_err) => {
        if (isMounted) {
          setHasError(true);
          setRemoteItems(null);
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => { isMounted = false; };
  }, [selectedCategory]);


  const filteredItems = remoteItems !== null
    ? remoteItems.map((item) => ({
        title: (isTe && item.titleTe) ? item.titleTe : item.title,
        cat: item.category || 'all',
        tier: item.tier || 'Party Setup',
        tierClass: item.tierClass || 'bg-tertiary-fixed text-on-tertiary-fixed',
        theme: item.themeTag || 'Celebration',
        time: item.time || '2h Slot',
        guests: item.guests || 'Up to 25 Guests',
        desc: (isTe && item.descriptionTe) ? item.descriptionTe : (item.description || item.desc),
        url: item.url,
      }))
    : [];

  return (
    <div className="w-full min-h-screen bg-background font-body-md text-on-surface antialiased">
      <Header />
      <main className="w-full pt-20 bg-background">
        <div className="flex flex-col w-full">
          {/* Header Banner */}
          <section className="relative w-full overflow-hidden bg-surface-container-low pb-space-xl pt-space-lg">
            <div className="relative max-w-7xl mx-auto px-gutter flex flex-col gap-space-lg">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-surface-container-lowest shadow-sm w-fit">
                <span className="material-symbols-outlined text-secondary text-base" style={{ fontVariationSettings: "'FILL' 1" }}>stars</span>
                <span className="font-label-sm text-label-sm text-primary uppercase tracking-wider font-bold">
                  Venue Showcase • Beside Durga Mart, Vadlamudi
                </span>
              </div>
              <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight font-bold">
                Explore Our Themes &amp; Real Celebration Setups
              </h1>
              <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl">
                See how families, romantic couples, and college squads transform Joybox for birthdays, private movie premieres, anniversaries, and surprise milestones in Guntur District.
              </p>

              {/* Category Filter Pills */}
              <div className="flex flex-wrap gap-2 pt-2">
                {[
                  { id: 'all', label: 'All Celebrations', count: 9 },
                  { id: 'birthday', label: 'Birthday Setups', count: 4 },
                  { id: 'anniversary', label: 'Anniversary & Romantic', count: 2 },
                  { id: 'kids', label: 'Kids Cartoon Special', count: 3 },
                  { id: 'adda', label: 'Adda & Screening', count: 2 },
                  { id: 'fx', label: 'Special FX in Action', count: 3 }
                ].map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setSelectedCategory(c.id)}
                    className={`px-4 py-2 rounded-full font-label-sm text-label-sm transition-all flex items-center gap-1.5 ${
                      selectedCategory === c.id
                        ? 'bg-primary text-on-primary shadow-sm font-bold'
                        : 'bg-surface-container-high text-on-surface hover:bg-surface-container-highest'
                    }`}
                  >
                    <span>{c.label}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                      selectedCategory === c.id ? 'bg-surface-container-highest text-primary' : 'bg-surface-container text-on-surface-variant'
                    }`}>
                      {c.count}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* Transparent Notice */}
          <section className="w-full max-w-7xl mx-auto px-gutter pt-space-lg">
            <div className="p-4 rounded-xl bg-surface-container flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-primary text-xl">verified_user</span>
                <p className="font-body-sm text-body-sm text-on-surface">
                  <strong>100% Honest Venue Showcase:</strong> All decors presented are built directly inside Joybox Vadlamudi. Balloon shades, neon signs, and cake plinths are completely customizable to your family's favorite palette. Host: Kiran Kumar (+91 78427 04429).
                </p>
              </div>
              <span className="shrink-0 font-label-sm text-label-sm px-3 py-1 rounded-full bg-surface-container-highest text-primary font-bold">
                Updated This Week
              </span>
            </div>
          </section>

          {/* Photo Grid */}
          <section className="w-full max-w-7xl mx-auto px-gutter py-space-xl">
            {loading && (
              <div className="mb-6 p-4 rounded-xl bg-surface-container flex items-center justify-center gap-2 text-primary">
                <span className="material-symbols-outlined animate-spin text-lg">sync</span>
                <span className="text-sm font-medium">Updating gallery showcase...</span>
              </div>
            )}
            {hasError && (
              <div className="mb-6 p-4 rounded-xl bg-error-container text-on-error-container text-sm flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-lg">error</span>
                  <span>Unable to load live gallery images from server. Showing local preview.</span>
                </div>
                <button
                  onClick={() => setSelectedCategory(selectedCategory)}
                  className="px-3 py-1 rounded bg-error text-on-error font-semibold text-xs"
                >
                  Retry
                </button>
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-space-lg">
              {filteredItems.map((item, idx) => (
                <div key={idx} className="group flex flex-col rounded-xl overflow-hidden bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300">
                  <div className="relative overflow-hidden aspect-[4/5] bg-surface-container">
                    <img
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                      alt={item.title}
                      src={item.url}
                      loading="eager"
                      decoding="sync"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-primary via-primary/20 to-transparent pointer-events-none"></div>
                    <div className="absolute top-4 left-4 flex flex-wrap gap-1.5">
                      <span className={`px-3 py-1 rounded-full font-label-sm text-label-sm shadow-sm font-bold ${item.tierClass}`}>
                        {item.tier}
                      </span>
                      <span className="px-3 py-1 rounded-full bg-surface-container-lowest text-primary font-label-sm text-label-sm font-semibold">
                        {item.theme}
                      </span>
                    </div>
                    <div className="absolute bottom-4 left-4 right-4 text-on-primary bg-primary rounded-lg px-3 py-2">
                      <div className="flex items-center gap-1.5 mb-1 text-tertiary-fixed font-label-sm text-label-sm font-bold">
                        <span>{item.time}</span>
                        <span>•</span>
                        <span>{item.guests}</span>
                      </div>
                      <h3 className="font-headline-sm text-lg text-on-primary font-bold leading-snug">
                        {item.title}
                      </h3>
                      <p className="font-body-sm text-xs text-primary-fixed mt-1 line-clamp-2">
                        {item.desc}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Gallery Booking CTA */}
          <section className="w-full max-w-7xl mx-auto px-gutter pb-space-2xl">
            <div className="rounded-2xl bg-gradient-to-r from-primary via-primary-container to-primary p-8 md:p-12 text-on-primary text-center flex flex-col items-center shadow-xl">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-tertiary-fixed text-on-tertiary-fixed font-label-sm text-xs uppercase font-bold tracking-wider mb-4">
                Bring Your Vision To Life
              </span>
              <h2 className="font-headline-lg text-2xl md:text-3xl font-bold mb-3 max-w-xl text-primary-fixed">
                Love What You See? Book Your Private Celebration Today
              </h2>
              <p className="font-body-md text-sm md:text-base text-primary-fixed-dim max-w-lg mb-6">
                Choose any decor style, customize balloon themes, and secure your hourly private slot in Vadlamudi.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-4">
                <Link
                  to="/booking?package=gold"
                  className="px-8 py-3.5 rounded-full bg-secondary text-on-secondary font-label-md font-bold shadow-lg hover:bg-secondary-container transition-all flex items-center gap-2"
                >
                  <span>Book Gold Package</span>
                  <span className="material-symbols-outlined text-lg">arrow_forward</span>
                </Link>
                <Link
                  to="/packages"
                  className="px-6 py-3 rounded-full bg-surface-container-lowest text-primary border border-outline font-label-md hover:bg-surface-container transition-all"
                >
                  Explore All Packages
                </Link>
              </div>
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
