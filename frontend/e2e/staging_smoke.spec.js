import { test, expect } from '@playwright/test';

test.describe('Staging Dry Run Smoke & Console Audits', () => {
  const publicPages = [
    { name: 'Landing Page', path: '/' },
    { name: 'Packages Page', path: '/packages' },
    { name: 'Booking Wizard', path: '/booking' },
    { name: 'Gallery Page', path: '/gallery' },
    { name: 'Contact Page', path: '/contact' },
    { name: 'Admin Login', path: '/admin/login' },
  ];

  for (const pageInfo of publicPages) {
    test(`verify ${pageInfo.name} has zero page errors and zero unvetted third-party requests`, async ({ page }) => {
      const pageErrors = [];
      const runtimeConsoleErrors = [];
      const thirdPartyRequests = [];

      // Intercept page errors (unhandled JS exceptions)
      page.on('pageerror', (err) => {
        pageErrors.push(err.message);
      });

      // Intercept console errors, filtering out expected HTTP 401 on initial unauthenticated session probe
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          const text = msg.text();
          // Filter expected 401 on initial /api/admin/auth/me probe
          if (text.includes('401') && text.includes('auth/me')) {
            return;
          }
          if (text.includes('Failed to load resource') && text.includes('401')) {
            return;
          }
          runtimeConsoleErrors.push(text);
        }
      });

      // Monitor network requests for unauthorized third-party destinations
      page.on('request', (req) => {
        const url = req.url();
        // Allow local Vite/Flask endpoints, data/blob URIs, and vetted Stitch design assets
        const isAllowed = 
          url.startsWith('http://127.0.0.1') || 
          url.startsWith('http://localhost') || 
          url.startsWith('data:') ||
          url.startsWith('blob:') ||
          url.startsWith('https://fonts.googleapis.com') ||
          url.startsWith('https://fonts.gstatic.com') ||
          url.startsWith('https://lh3.googleusercontent.com') ||
          url.startsWith('https://checkout.razorpay.com');

        if (!isAllowed) {
          thirdPartyRequests.push(url);
        }
      });

      // Mock Razorpay CDN checkout script with empty 200 JS to prevent net::ERR_FAILED console noise
      await page.route('**/*checkout.razorpay.com/**', (route) => 
        route.fulfill({
          status: 200,
          contentType: 'application/javascript',
          body: '/* Mocked Razorpay SDK in staging smoke */'
        })
      );

      const response = await page.goto(pageInfo.path, { waitUntil: 'domcontentloaded' });
      expect(response.status()).toBeLessThan(400);

      // Wait 1 second for any delayed async renders or effects
      await page.waitForTimeout(1000);

      // Assert zero unhandled JS exceptions
      expect(pageErrors, `Found uncaught page exceptions on ${pageInfo.name}: ${pageErrors.join('; ')}`).toEqual([]);

      // Assert zero unexpected console errors
      expect(runtimeConsoleErrors, `Found console errors on ${pageInfo.name}: ${runtimeConsoleErrors.join('; ')}`).toEqual([]);

      // Assert zero third-party network leaks
      expect(thirdPartyRequests, `Found unauthorized third-party requests on ${pageInfo.name}: ${thirdPartyRequests.join('; ')}`).toEqual([]);
    });
  }

  test('backend health and security headers verification', async ({ request }) => {
    // Probe backend directly on port 5000
    const res = await request.get('http://127.0.0.1:5000/api/health');
    expect(res.status()).toBe(200);
    const headers = res.headers();
    expect(headers['x-content-type-options']).toBe('nosniff');
    expect(headers['x-frame-options']).toBe('DENY');
    expect(headers['x-request-id']).toBeTruthy();
  });
});
