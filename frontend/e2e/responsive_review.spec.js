import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOTS_DIR = path.resolve(__dirname, '../../Reports/docs/responsive-review/screenshots');
const METRICS_FILE = path.resolve(__dirname, '../../Reports/docs/responsive-review/audit-metrics.json');

// Ensure output dirs exist
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

const ALL_VIEWPORTS = [
  // Mobile
  { name: 'mobile-320', width: 320, height: 568, category: 'mobile' },
  { name: 'mobile-360', width: 360, height: 800, category: 'mobile' },
  { name: 'mobile-375', width: 375, height: 667, category: 'mobile' },
  { name: 'mobile-390', width: 390, height: 844, category: 'mobile', key: true },
  { name: 'mobile-412', width: 412, height: 915, category: 'mobile' },
  // Tablet
  { name: 'tablet-768', width: 768, height: 1024, category: 'tablet', key: true },
  { name: 'tablet-820', width: 820, height: 1180, category: 'tablet' },
  { name: 'tablet-1024h', width: 1024, height: 768, category: 'tablet' },
  { name: 'tablet-1024v', width: 1024, height: 1366, category: 'tablet' },
  // Desktop
  { name: 'desktop-1280', width: 1280, height: 720, category: 'desktop', key: true },
  { name: 'desktop-1366', width: 1366, height: 768, category: 'desktop' },
  { name: 'desktop-1440', width: 1440, height: 900, category: 'desktop' },
  { name: 'desktop-1536', width: 1536, height: 864, category: 'desktop' },
  { name: 'desktop-1920', width: 1920, height: 1080, category: 'desktop', key: true },
];

const PAGES = [
  { path: '/', slug: 'home', name: 'Home Landing' },
  { path: '/packages', slug: 'packages', name: 'Packages & Rates' },
  { path: '/add-ons', slug: 'add-ons', name: 'Add-ons Showcase' },
  { path: '/booking', slug: 'booking', name: 'Booking Engine' },
  { path: '/gallery', slug: 'gallery', name: 'Photo Gallery' },
  { path: '/contact', slug: 'contact', name: 'Contact & Location' },
  { path: '/terms', slug: 'terms', name: 'Terms of Service' },
  { path: '/privacy', slug: 'privacy', name: 'Privacy Policy' },
  { path: '/refund-policy', slug: 'refund-policy', name: 'Cancellation & Refund' },
];

test.describe('Responsive Layout, A11y & Visual Quality Review', () => {
  test('audit all 9 pages across 14 viewports in English and Telugu with screenshots & zero horizontal overflow', async ({ page }) => {
    test.setTimeout(240000);

    const auditResults = {
      timestamp: new Date().toISOString(),
      viewportsCount: ALL_VIEWPORTS.length,
      pagesCount: PAGES.length,
      overflowAudits: [],
      screenshots: [],
      vitals: {},
      a11yViolations: {},
    };

    for (const pageInfo of PAGES) {
      for (const lang of ['en', 'te']) {
        // Set viewport to key desktop to switch language cleanly
        await page.setViewportSize({ width: 1280, height: 720 });
        await page.goto(pageInfo.path, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(400);

        // Switch language if needed
        if (lang === 'te') {
          const teButton = page.locator('[data-testid="language-switch"] button').filter({ hasText: 'తెలుగు' });
          if (await teButton.isVisible()) {
            await teButton.click();
            await page.waitForTimeout(300);
          }
        }

        // Measure Core Web Vitals on English run at key desktop
        if (lang === 'en' && ['home', 'packages', 'booking'].includes(pageInfo.slug)) {
          const vitals = await page.evaluate(() => {
            const paint = performance.getEntriesByType('paint');
            let fcp = 0;
            for (const p of paint) {
              if (p.name === 'first-contentful-paint') fcp = Math.round(p.startTime);
            }
            const nav = performance.getEntriesByType('navigation')[0];
            return {
              fcp,
              domContentLoaded: nav ? Math.round(nav.domContentLoadedEventEnd) : 0,
              loadTime: nav ? Math.round(nav.loadEventEnd) : 0,
            };
          });
          auditResults.vitals[pageInfo.slug] = vitals;

          // Run Axe A11y scan
          const axeResults = await new AxeBuilder({ page })
            .withTags(['wcag2a', 'wcag2aa'])
            .analyze();
          const critical = axeResults.violations.filter((v) => v.impact === 'critical');
          auditResults.a11yViolations[pageInfo.slug] = {
            criticalCount: critical.length,
            violations: axeResults.violations.map((v) => ({ id: v.id, impact: v.impact, description: v.description })),
          };
          expect(critical, `Critical a11y violations on ${pageInfo.name}`).toEqual([]);
        }

        // Now test across viewports
        for (const vp of ALL_VIEWPORTS) {
          await page.setViewportSize({ width: vp.width, height: vp.height });
          await page.waitForTimeout(150);

          // Check horizontal overflow
          const overflow = await page.evaluate(() => {
            const doc = document.documentElement;
            return doc.scrollWidth - doc.clientWidth;
          });

          const auditRecord = {
            page: pageInfo.slug,
            lang,
            viewport: vp.name,
            width: vp.width,
            height: vp.height,
            overflow,
            pass: overflow <= 1,
          };
          auditResults.overflowAudits.push(auditRecord);

          expect(overflow, `Horizontal overflow on ${pageInfo.slug} at ${vp.width}x${vp.height} (${lang})`).toBeLessThanOrEqual(1);

          // Capture screenshot for key viewports
          if (vp.key) {
            const filename = `${pageInfo.slug}_${lang}_${vp.width}x${vp.height}.png`;
            const filepath = path.join(SCREENSHOTS_DIR, filename);
            await page.screenshot({ path: filepath, fullPage: false });
            auditResults.screenshots.push({
              page: pageInfo.slug,
              name: pageInfo.name,
              lang,
              viewport: vp.name,
              dimensions: `${vp.width}x${vp.height}`,
              filename,
            });
          }
        }
      }
    }

    // Save metrics
    fs.writeFileSync(METRICS_FILE, JSON.stringify(auditResults, null, 2), 'utf-8');
    console.log(`[AUDIT COMPLETE] Audited ${auditResults.overflowAudits.length} viewport/page combinations. Captured ${auditResults.screenshots.length} key screenshots.`);
  });
});
