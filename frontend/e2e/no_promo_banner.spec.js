import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'desktop-1920', width: 1920, height: 1080 },
  { name: 'mobile-390', width: 390, height: 844 },
];

const PAGES = [
  '/',
  '/packages',
  '/booking',
  '/gallery',
  '/contact',
  '/terms',
  '/privacy',
  '/refund-policy',
  '/admin/login',
  '/admin',
  '/mobile-booking',
  '/booking-status',
  '/this-route-does-not-exist',
];

const BANNED = [
  'Special Introductory Offer',
  'first 5 eligible monthly bookings',
  'తెలుగు అందుబాటులో ఉంది',
  'ప్రత్యేక ఆఫర్: నెలకు మొదటి 5',
  '✨ Special Introductory',
];

async function assertNoPromoBar(page, path) {
  const response = await page.goto(path, { waitUntil: 'domcontentloaded' });
  expect(response.status(), path).toBeLessThan(400);

  const header = page.locator('header').first();
  await expect(header, `${path} header`).toBeVisible();

  const bodyText = await page.locator('body').innerText();
  for (const phrase of BANNED) {
    expect(bodyText, `${path} still shows "${phrase}"`).not.toContain(phrase);
  }

  const box = await header.boundingBox();
  expect(box, `${path} header box`).not.toBeNull();
  expect(box.y, `${path} navbar top`).toBeGreaterThanOrEqual(0);
  expect(box.y, `${path} navbar top`).toBeLessThan(1);

  if (path === '/booking') {
    const dateStep = page.getByRole('button', { name: /Date & Slot/i });
    if (await dateStep.count()) {
      await dateStep.first().click();
      const stepText = await page.locator('body').innerText();
      for (const phrase of BANNED) {
        expect(stepText, `booking step still shows "${phrase}"`).not.toContain(phrase);
      }
      const stepBox = await page.locator('header').first().boundingBox();
      expect(stepBox.y, 'booking step navbar top').toBeLessThan(1);
    }
  }
}

for (const viewport of VIEWPORTS) {
  test(`navbar top is 0 and the introductory offer bar is absent (${viewport.name})`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const path of PAGES) {
      await assertNoPromoBar(page, path);
    }

    await page.goto('/', { waitUntil: 'domcontentloaded' });
    const telugu = page.getByRole('button', { name: 'తెలుగు' });
    if (await telugu.count()) {
      await telugu.first().click();
      const switched = await page.locator('body').innerText();
      for (const phrase of BANNED) {
        expect(switched, `after language switch still shows "${phrase}"`).not.toContain(phrase);
      }
      const box = await page.locator('header').first().boundingBox();
      expect(box.y).toBeLessThan(1);
    }
  });
}
