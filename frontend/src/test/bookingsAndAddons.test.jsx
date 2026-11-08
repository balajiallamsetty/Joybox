import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import BookingsClosedNotice from '../components/BookingsClosedNotice';
import AddonsPage from '../pages/AddonsPage';
import { LanguageProvider } from '../components/LanguageContext';

vi.mock('../services/api', () => ({
  api: {
    getAddOns: vi.fn(),
    getPublicConfig: vi.fn(),
  },
}));

import { api } from '../services/api';

describe('BookingsClosedNotice Component', () => {
  it('renders accessible alert banner with role status and WhatsApp CTA in English', () => {
    render(
      <LanguageProvider>
        <BookingsClosedNotice whatsappNumber="+91 78427 04429" />
      </LanguageProvider>
    );

    const banner = screen.getByTestId('bookings-closed-notice');
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveAttribute('role', 'status');
    expect(banner).toHaveAttribute('aria-live', 'polite');
    expect(screen.getByText(/Online Bookings Are Currently Closed/i)).toBeInTheDocument();

    const waBtn = screen.getByTestId('bookings-closed-wa-btn');
    expect(waBtn).toBeInTheDocument();
    expect(waBtn.getAttribute('href')).toContain('https://wa.me/917842704429');
  });

  it('renders Telugu copy when language context is te', () => {
    render(
      <LanguageProvider>
        <BookingsClosedNotice whatsappNumber="917842704429" />
      </LanguageProvider>
    );
    expect(screen.getByTestId('bookings-closed-notice')).toBeInTheDocument();
  });
});

describe('AddonsPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders add-on cards and bookings closed notice when bookingsOpen is false', async () => {
    api.getAddOns.mockResolvedValueOnce({
      items: [
        {
          code: 'bubble_entry',
          name: 'Bubble Machine Entry',
          nameTe: 'బుడగల మెషిన్ ఎంట్రీ',
          description: 'Magical floating bubbles for cake cutting entry',
          priceMinor: 30000,
          currency: 'INR',
          iconSymbol: 'bubble_chart',
        },
      ],
    });

    api.getPublicConfig.mockResolvedValueOnce({
      data: {
        bookingsOpen: false,
        paymentsEnabled: false,
        whatsappNumber: '917842704429',
      },
    });

    render(
      <MemoryRouter initialEntries={['/add-ons']}>
        <LanguageProvider>
          <AddonsPage />
        </LanguageProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('bookings-closed-notice')).toBeInTheDocument();
    });

    expect(screen.getByText('Bubble Machine Entry')).toBeInTheDocument();
    expect(screen.getByText('₹300')).toBeInTheDocument();

    const bookWithAddonBtn = screen.getByRole('link', { name: /Book With This Add-on/i });
    expect(bookWithAddonBtn).toHaveAttribute('href', '/booking?addons=bubble_entry');
  });
});
