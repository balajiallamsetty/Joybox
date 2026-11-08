import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { LanguageProvider } from '../components/LanguageContext';
import BookingWizardPage from '../pages/BookingWizardPage';
import BookingStatusPage from '../pages/BookingStatusPage';
import { api } from '../services/api';

describe('Frontend API Error Handling & Empty States', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders clean empty state when no slots are available for selected date', async () => {
    vi.spyOn(api, 'getPackages').mockResolvedValue({
      items: [{ code: 'gold', name: 'Gold', pricePerHourMinor: 150000 }],
    });

    vi.spyOn(api, 'getAvailability').mockResolvedValue({
      date: '2026-12-25',
      durationHours: 2,
      slots: [],
    });

    render(
      <LanguageProvider>
        <MemoryRouter initialEntries={['/booking?package=gold&date=2026-12-25']}>
          <BookingWizardPage />
        </MemoryRouter>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/No slots available for 2026-12-25/i)).toBeInTheDocument();
    });
  });

  it('displays user-friendly error banner when availability API fails', async () => {
    vi.spyOn(api, 'getPackages').mockResolvedValue({
      items: [{ code: 'gold', name: 'Gold', pricePerHourMinor: 150000 }],
    });

    vi.spyOn(api, 'getAvailability').mockRejectedValue(
      new Error('Live calendar network timeout. Please retry.')
    );

    render(
      <LanguageProvider>
        <MemoryRouter initialEntries={['/booking?package=gold&date=2026-12-25']}>
          <BookingWizardPage />
        </MemoryRouter>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Live calendar network timeout/i)).toBeInTheDocument();
    });
  });

  it('renders not-found state on BookingStatusPage when booking reference does not exist', async () => {
    global.fetch = vi.fn().mockImplementation(async (url) => {
      if (url.includes('/api/bookings/JB-NONEXISTENT')) {
        return {
          ok: false,
          json: async () => ({
            success: false,
            error: { code: 'NOT_FOUND', message: 'Booking reference not found in registry.' },
          }),
        };
      }
      return { ok: false, json: async () => ({}) };
    });

    render(
      <LanguageProvider>
        <MemoryRouter initialEntries={['/booking/JB-NONEXISTENT']}>
          <Routes>
            <Route path="/booking/:ref" element={<BookingStatusPage />} />
          </Routes>
        </MemoryRouter>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Booking Not Found/i)).toBeInTheDocument();
      expect(screen.getByText(/Booking reference not found in registry/i)).toBeInTheDocument();
    });
  });
});

