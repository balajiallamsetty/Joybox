import { test, expect } from '@playwright/test';

test.describe('Bookings Closed & Add-ons Showcase E2E', () => {
  test('navigates to /add-ons, displays celebration add-ons, and links to booking with ?addons=', async ({ page }) => {
    await page.goto('/add-ons');

    // Header and Hero check
    await expect(page.locator('h1')).toContainText(/Make Every Moment Extraordinary|మీ వేడుకను మరింత ఘనంగా మార్చుకోండి/i);

    // Addons grid visible
    const addonsGrid = page.locator('[data-testid="addons-grid"]');
    await expect(addonsGrid).toBeVisible();

    // Check first card has a CTA linking to booking
    const bookWithAddonBtn = page.locator('[data-testid="addons-grid"] a').first();
    await expect(bookWithAddonBtn).toBeVisible();
    const href = await bookWithAddonBtn.getAttribute('href');
    expect(href).toMatch(/\/booking\?addons=/);

    // Click the CTA and confirm navigation to /booking
    await bookWithAddonBtn.click();
    await page.waitForURL(/\/booking\?addons=/);
    expect(page.url()).toContain('addons=');
  });

  test('displays BookingsClosedNotice on /booking when bookingsOpen is false', async ({ page }) => {
    // Intercept /api/public-config to return bookingsOpen: false
    await page.route('**/api/public-config', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            bookingsOpen: false,
            paymentsEnabled: false,
            whatsappNumber: '917842704429',
            venue: {
              name: 'Joybox Party Room',
              location: 'Vadlamudi, Guntur',
              hours: '9:00 AM - 10:00 PM IST',
              host: 'Kiran Kumar',
            },
          },
        }),
      });
    });

    await page.goto('/booking');

    // Verify BookingsClosedNotice is rendered prominently
    const notice = page.locator('[data-testid="bookings-closed-notice"]');
    await expect(notice).toBeVisible();
    await expect(notice).toContainText(/Online Bookings Are Currently Closed|ఆన్‌లైన్ బుకింగ్‌లు/i);

    // Verify WhatsApp button inside notice
    const waBtn = page.locator('[data-testid="bookings-closed-wa-btn"]');
    await expect(waBtn).toBeVisible();
    const waHref = await waBtn.getAttribute('href');
    expect(waHref).toContain('wa.me/917842704429');
  });

  test('allows toggling add-ons on Step 2 of Booking Wizard', async ({ page }) => {
    await page.goto('/booking?package=gold');

    // Should land directly on Step 2 since package=gold is in URL
    const addonsSection = page.locator('[data-testid="wizard-addons-section"]');
    await expect(addonsSection).toBeVisible();

    // Check an add-on checkbox
    const firstCheckbox = addonsSection.locator('input[type="checkbox"]').first();
    await expect(firstCheckbox).toBeVisible();
    const isCheckedInitially = await firstCheckbox.isChecked();
    await firstCheckbox.click();
    expect(await firstCheckbox.isChecked()).toBe(!isCheckedInitially);
  });
});
