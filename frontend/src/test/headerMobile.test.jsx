import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Header from '../components/Header';
import { LanguageProvider } from '../components/LanguageContext';

describe('Header Mobile Navigation', () => {
  it('toggles mobile navigation drawer on hamburger button click with accessible attributes', () => {
    render(
      <LanguageProvider>
        <MemoryRouter initialEntries={['/']}>
          <Header />
        </MemoryRouter>
      </LanguageProvider>
    );

    const toggle = screen.getByTestId('mobile-menu-toggle');
    expect(toggle).toBeInTheDocument();
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    // Open drawer
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const drawer = screen.getByTestId('mobile-nav-drawer');
    expect(drawer).toBeInTheDocument();

    // Verify all mobile nav links are accessible
    expect(screen.getAllByText('Packages & Add-ons').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Book Venue').length).toBeGreaterThanOrEqual(1);

    // Close drawer
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByTestId('mobile-nav-drawer')).not.toBeInTheDocument();
  });
});
