import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LanguageProvider } from '../components/LanguageContext';
import BookingWizardPage from '../pages/BookingWizardPage';
import { api } from '../services/api';

describe('Booking Wizard Form Validation & Step Navigation', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    vi.spyOn(api, 'getPackages').mockResolvedValue({
      items: [
        { code: 'gold', name: 'Gold Celebration', pricePerHourMinor: 150000, description: 'Gold tier' },
      ],
    });

    vi.spyOn(api, 'getAvailability').mockResolvedValue({
      date: '2026-12-01',
      durationHours: 2,
      slots: [
        { startTime: '10:00', endTime: '12:00', available: true },
      ],
    });

    vi.spyOn(api, 'getQuote').mockResolvedValue({
      packageCode: 'gold',
      durationHours: 2,
      baseAmountRupees: 3000,
      totalRupees: 3000,
      lineItems: [
        { description: 'Gold Celebration (2 hrs)', amountRupees: 3000, amountMinor: 300000 },
      ],
    });
  });

  it('rejects invalid/short phone numbers on Step 3 and allows valid 10-digit numbers to proceed to Step 4', async () => {
    render(
      <LanguageProvider>
        <MemoryRouter initialEntries={['/booking?package=gold&date=2026-12-01']}>
          <BookingWizardPage />
        </MemoryRouter>
      </LanguageProvider>
    );

    // 1. Wait for slot to be visible on Step 2
    await waitFor(() => {
      expect(screen.getByText('10:00')).toBeInTheDocument();
    });

    // Select slot
    fireEvent.click(screen.getByText('10:00'));

    // Click "Next: Celebrant Details"
    const nextToStep3Btn = screen.getByText(/Next: Celebrant Details/i);
    expect(nextToStep3Btn).not.toBeDisabled();
    fireEvent.click(nextToStep3Btn);

    // 2. Step 3 should be displayed
    await waitFor(() => {
      expect(screen.getByText(/Step 3: Celebrant & Contact Info/i)).toBeInTheDocument();
    });

    const phoneInput = screen.getByPlaceholderText(/9876543210/i);
    const nextToStep4Btn = screen.getByText(/Next: Review & Lock/i);

    // Attempt to proceed with invalid phone (short)
    fireEvent.change(phoneInput, { target: { value: '12345' } });
    fireEvent.click(nextToStep4Btn);

    // Verify error is displayed and still on Step 3
    await waitFor(() => {
      expect(screen.getByText(/Please enter a valid 10-digit mobile number/i)).toBeInTheDocument();
      expect(screen.getByText(/Step 3: Celebrant & Contact Info/i)).toBeInTheDocument();
    });

    // Enter valid 10-digit phone
    fireEvent.change(phoneInput, { target: { value: '9876543210' } });
    const celebrantInput = screen.getByPlaceholderText(/Priya/i);
    fireEvent.change(celebrantInput, { target: { value: 'Aarav' } });

    fireEvent.click(nextToStep4Btn);

    // 3. Step 4 (Reservation Summary & Lock) should now be displayed
    await waitFor(() => {
      expect(screen.getByText(/Step 4: Reservation Summary & Lock/i)).toBeInTheDocument();
      expect(screen.getByText(/Aarav/i)).toBeInTheDocument();
      expect(screen.getByText(/9876543210/i)).toBeInTheDocument();
    });

    // Back button returns to Step 3
    const backToStep3Btn = screen.getByText(/← Back/i);
    fireEvent.click(backToStep3Btn);

    await waitFor(() => {
      expect(screen.getByText(/Step 3: Celebrant & Contact Info/i)).toBeInTheDocument();
    });
  });
});
