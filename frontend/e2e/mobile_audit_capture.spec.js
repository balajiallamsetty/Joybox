import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const MOBILE_AUDIT_DIR = path.resolve(__dirname, '../../Reports/mobile-audit');

test.describe('Mobile Viewport Audit & Screenshot Capture', () => {
  const VIEWPORTS = [
    { name: '320x568_se', width: 320, height: 568 },
    { name: '360x640_android', width: 360, height: 640 },
    { name: '375x667_iphone8', width: 375, height: 667 },
    { name: '390x844_iphone14', width: 390, height: 844 },
    { name: '414x896_xr', width: 414, height: 896 },
    { name: '768x1024_ipad', width: 768, height: 1024 },
    { name: '844x390_landscape', width: 844, height: 390 },
  ];

  const ROUTES = [
    { path: '/', slug: 'home' },
    { path: '/packages', slug: 'packages' },
    { path: '/booking', slug: 'booking' },
    { path: '/gallery', slug: 'gallery' },
    { path: '/contact', slug: 'contact' },
    { path: '/terms', slug: 'terms' },
    { path: '/privacy', slug: 'privacy' },
    { path: '/refund-policy', slug: 'refund-policy' },
  ];

  test('capture all requested viewports and assert zero horizontal overflow', async ({ page }) => {
    test.setTimeout(180000);

    const overflowFailures = [];

    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      for (const route of ROUTES) {
        await page.goto(route.path, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(200);

        // Check for horizontal overflow
        const overflow = await page.evaluate(() => {
          return {
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
            hasOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
          };
        });

        if (overflow.hasOverflow) {
          overflowFailures.push({
            route: route.path,
            viewport: vp.name,
            scrollWidth: overflow.scrollWidth,
            clientWidth: overflow.clientWidth,
          });
        }

        const screenshotPath = path.join(
          MOBILE_AUDIT_DIR,
          `${route.slug}_${vp.name}.png`
        );
        await page.screenshot({ path: screenshotPath, fullPage: false });
      }

      // If mobile (< 1024), test mobile hamburger drawer
      if (vp.width < 1024) {
        await page.goto('/', { waitUntil: 'domcontentloaded' });
        const toggle = page.locator('[data-testid="mobile-menu-toggle"]');
        if (await toggle.isVisible()) {
          await toggle.click();
          await page.waitForTimeout(250);
          const menuScreenshot = path.join(
            MOBILE_AUDIT_DIR,
            `mobile_nav_drawer_${vp.name}.png`
          );
          await page.screenshot({ path: menuScreenshot, fullPage: false });
          await toggle.click();
        }
      }
    }

    expect(overflowFailures).toEqual([]);
  });
});
