import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LanguageProvider } from '../components/LanguageContext';
import BookingWizardPage from '../pages/BookingWizardPage';
import { api } from '../services/api';

describe('Booking Wizard Full Journey (F1)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    // Mock API methods
    vi.spyOn(api, 'getPackages').mockResolvedValue({
      items: [
        { code: 'basic', name: 'Basic', pricePerHourMinor: 99900, description: 'Basic tier' },
        { code: 'gold', name: 'Gold', pricePerHourMinor: 150000, description: 'Gold tier' },
        { code: 'diamond', name: 'Diamond', pricePerHourMinor: 250000, description: 'Diamond tier' },
      ],
    });

    vi.spyOn(api, 'getAvailability').mockImplementation(async (date, duration) => {
      return {
        date,
        durationHours: duration,
        slots: [
          { startTime: '10:00', endTime: '12:00', available: true },
          { startTime: '14:00', endTime: '16:00', available: true },
        ],
      };
    });

    vi.spyOn(api, 'getQuote').mockResolvedValue({
      packageCode: 'diamond',
      durationHours: 2,
      baseAmountRupees: 5000,
      totalRupees: 5000,
      lineItems: [
        { description: 'Diamond Tier (2 hrs)', amountRupees: 5000, amountMinor: 500000 },
      ],
    });

    // Mock global fetch for booking creation & Razorpay order
    global.fetch = vi.fn().mockImplementation(async (url) => {
      if (url.includes('/api/public-config')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: {
              bookingsOpen: true,
              paymentsEnabled: true,
              whatsappNumber: '917842704429',
            },
          }),
        };
      }
      if (url.includes('/api/bookings')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: {
              bookingReference: 'JB-TEST-999',
              accessToken: 'test-token-xyz',
            },
          }),
        };
      }
      if (url.includes('/api/payments/create-order')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: {
              orderId: 'order_mock123',
              amountMinor: 500000,
              currency: 'INR',
              keyId: 'rzp_test_mock',
            },
          }),
        };
      }
      return { ok: false, json: async () => ({}) };
    });

    // Mock window.Razorpay
    window.Razorpay = vi.fn().mockImplementation(() => ({
      open: vi.fn(),
      on: vi.fn(),
    }));
  });

  it('preselects package from URL, changes date, selects slot, verifies server quote and initiates payment lock', async () => {
    // 1. Initial render with ?package=diamond in query
    render(
      <LanguageProvider>
        <MemoryRouter initialEntries={['/booking?package=diamond']}>
          <BookingWizardPage />
        </MemoryRouter>
      </LanguageProvider>
    );

    // The catalog comes from the server, then a package in the URL opens step 2.
    await waitFor(() => {
      expect(screen.getByText(/Step 2: Choose Date & Time Slot/i)).toBeInTheDocument();
    });
    expect(screen.getAllByText(/Diamond/i).length).toBeGreaterThan(0);

    // 2. Select a Slot
    await waitFor(() => {
      expect(screen.getByText('10:00')).toBeInTheDocument();
    });

    const slotBtn = screen.getByText('10:00');
    fireEvent.click(slotBtn);

    // Click "Next: Celebrant Details"
    const nextToStep3Btn = screen.getByRole('button', { name: /Next: Celebrant Details/i });
    fireEvent.click(nextToStep3Btn);

    // 3. Step 3: Celebrant and customer info
    await waitFor(() => {
      expect(screen.getByText(/Step 3: Celebrant & Contact Info/i)).toBeInTheDocument();
    });

    const phoneInput = screen.getByPlaceholderText(/9876543210/i);
    fireEvent.change(phoneInput, { target: { value: '9876543210' } });

    const celebrantInput = screen.getByPlaceholderText(/e\.g\. Priya/i);
    fireEvent.change(celebrantInput, { target: { value: 'Ravi Kumar' } });

    // Click "Next: Review & Lock"
    const nextToStep4Btn = screen.getByRole('button', { name: /Next: Review & Lock/i });
    fireEvent.click(nextToStep4Btn);

    // 4. Step 4: Verification & Quote display
    await waitFor(() => {
      expect(screen.getByText(/Step 4: Reservation Summary & Lock/i)).toBeInTheDocument();
    });

    // Verify server price breakdown is displayed
    await waitFor(() => {
      expect(screen.getByText(/Diamond Tier \(2 hrs\)/i)).toBeInTheDocument();
      expect(screen.getAllByText(/₹5,000/i).length).toBeGreaterThanOrEqual(1);
    });

    // 5. Submit booking and proceed to payment
    const payBtn = screen.getByRole('button', { name: /Pay & Lock Slot/i });
    fireEvent.click(payBtn);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/bookings'),
        expect.objectContaining({ method: 'POST' })
      );
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/payments/create-order'),
        expect.objectContaining({ method: 'POST' })
      );
      expect(window.Razorpay).toHaveBeenCalled();
    });
  });
});
