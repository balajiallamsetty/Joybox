import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import BookingsOpeningSoon from '../components/BookingsOpeningSoon';

describe('BookingsOpeningSoon Modal Component', () => {
  it('does not render when isOpen is false', () => {
    const { container } = render(
      <BookingsOpeningSoon isOpen={false} onClose={vi.fn()} packageName="Gold" />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders modal dialog with accessible attributes, heading, and package name when isOpen is true', () => {
    render(
      <BookingsOpeningSoon isOpen={true} onClose={vi.fn()} packageName="Gold" />
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'bookings-opening-soon-title');
    expect(dialog).toHaveAttribute('aria-describedby', 'bookings-opening-soon-desc');

    expect(screen.getByRole('heading', { level: 2, name: /bookings opening soon/i })).toBeInTheDocument();
    expect(screen.getByText(/Gold\s+Package/i)).toBeInTheDocument();
    expect(
      screen.getByText(/to reserve a slot, please contact us on whatsapp/i)
    ).toBeInTheDocument();
  });

  it('constructs correct WhatsApp deep link with prefilled encoded message', () => {
    render(
      <BookingsOpeningSoon isOpen={true} onClose={vi.fn()} packageName="Diamond" />
    );

    const waLink = screen.getByRole('link', { name: /contact on whatsapp/i });
    expect(waLink).toBeInTheDocument();
    expect(waLink).toHaveAttribute('target', '_blank');
    expect(waLink).toHaveAttribute('rel', 'noopener noreferrer');

    const expectedHref =
      'https://wa.me/917842704429?text=' +
      encodeURIComponent("Hi Joybox! I'd like to book a slot for the Diamond package.");
    expect(waLink).toHaveAttribute('href', expectedHref);
  });

  it('triggers onClose when clicking the close button', () => {
    const handleClose = vi.fn();
    render(
      <BookingsOpeningSoon isOpen={true} onClose={handleClose} packageName="Basic" />
    );

    const closeBtn = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('triggers onClose when clicking the backdrop', () => {
    const handleClose = vi.fn();
    render(
      <BookingsOpeningSoon isOpen={true} onClose={handleClose} packageName="Basic" />
    );

    const backdrop = screen.getByTestId('bookings-opening-soon-backdrop');
    fireEvent.click(backdrop);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('triggers onClose when pressing the Escape key', () => {
    const handleClose = vi.fn();
    render(
      <BookingsOpeningSoon isOpen={true} onClose={handleClose} packageName="Basic" />
    );

    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
