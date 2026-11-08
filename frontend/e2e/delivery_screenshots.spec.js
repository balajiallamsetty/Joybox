import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OUT_DIR = path.resolve(__dirname, '../../Reports/docs/delivery-screenshots');

test.describe('Clean Delivery Screenshots Capture', () => {
  test('capture clean first-time visitor screenshots across all key pages', async ({ page }) => {
    // 1. Home desktop & mobile
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, '01_home_desktop.png') });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(OUT_DIR, '01_home_mobile.png') });

    // 2. Packages desktop & mobile
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/packages');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, '02_packages_desktop.png') });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(OUT_DIR, '02_packages_mobile.png') });

    // 3. Add-ons showcase
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/add-ons');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, '03_addons_desktop.png') });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(OUT_DIR, '03_addons_mobile.png') });

    // 4. Booking Wizard Initial State
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/booking');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, '04_booking_step1_desktop.png') });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(OUT_DIR, '04_booking_step1_mobile.png') });

    // 5. Booking Wizard Step 2 (Slots & Addons)
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/booking?package=gold');
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(OUT_DIR, '05_booking_step2_slots_and_addons.png') });

    // 6. Gallery
    await page.goto('/gallery');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, '06_gallery_desktop.png') });

    // 7. Contact
    await page.goto('/contact');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, '07_contact_desktop.png') });

    // 8. Terms
    await page.goto('/terms');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, '08_terms_desktop.png') });

    // 9. Privacy
    await page.goto('/privacy');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, '09_privacy_desktop.png') });

    // 10. Refund Policy
    await page.goto('/refund-policy');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, '10_refund_policy_desktop.png') });
  });
});
