import { test, expect } from '@playwright/test';

async function emptyCatalog(page) {
  const empty = { success: true, data: { items: [], offers: [] }, error: null };
  await page.route('**/api/packages**', (route) => route.fulfill({ json: empty }));
  await page.route('**/api/add-ons**', (route) => route.fulfill({ json: empty }));
  await page.route('**/api/offers/active**', (route) => route.fulfill({ json: { success: true, data: { offers: [] }, error: null } }));
}

test('empty catalog keeps booking closed', async ({ page }) => {
  await emptyCatalog(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByText('Bookings open soon').first()).toBeVisible();
  await expect(page.getByText('₹999')).toHaveCount(0);
  await expect(page.getByText('₹500/hour')).toHaveCount(0);

  await page.goto('/packages');
  await expect(page.getByText('Bookings open soon').first()).toBeVisible();

  await page.goto('/booking');
  await expect(page.getByRole('button', { name: /Continue with/i })).toHaveCount(0);
  await expect(page.getByText('Bookings open soon').first()).toBeVisible();

  await page.goto('/mobile-booking');
  await expect(page.getByText('Bookings open soon').first()).toBeVisible();
  await expect(page.getByText('Celebrant')).toHaveCount(0);
});
