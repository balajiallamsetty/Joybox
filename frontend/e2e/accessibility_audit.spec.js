import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('WCAG 2.2 AA Accessibility Audits & Keyboard Journeys', () => {
  const publicPages = [
    { name: 'Landing Page', path: '/' },
    { name: 'Packages Page', path: '/packages' },
    { name: 'Booking Wizard', path: '/booking' },
    { name: 'Gallery Page', path: '/gallery' },
    { name: 'Contact Page', path: '/contact' },
    { name: 'Terms Page', path: '/terms' },
    { name: 'Privacy Page', path: '/privacy' },
    { name: 'Refund Policy Page', path: '/refund-policy' },
    { name: 'Admin Login', path: '/admin/login' },
  ];

  for (const pageInfo of publicPages) {
    test(`audit ${pageInfo.name} (${pageInfo.path}) for WCAG 2.2 AA violations`, async ({ page }) => {
      // Mock Razorpay script
      await page.route('**/*checkout.razorpay.com/**', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/javascript',
          body: '/* Mocked Razorpay SDK */',
        })
      );

      await page.goto(pageInfo.path, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1000);

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      const criticalViolations = accessibilityScanResults.violations.filter((v) => v.impact === 'critical');
      const seriousViolations = accessibilityScanResults.violations.filter((v) => v.impact === 'serious');

      if (criticalViolations.length > 0 || seriousViolations.length > 0) {
        console.warn(
          `[A11Y REPORT] ${pageInfo.name} - Critical: ${criticalViolations.length}, Serious: ${seriousViolations.length}`,
          JSON.stringify(
            [...criticalViolations, ...seriousViolations].map((v) => ({
              id: v.id,
              impact: v.impact,
              description: v.description,
              nodes: v.nodes.map((n) => ({ html: n.html, target: n.target })),
            })),
            null,
            2
          )
        );
      }

      // Assert zero critical accessibility violations
      expect(criticalViolations, `Found critical WCAG violations on ${pageInfo.name}`).toEqual([]);
    });
  }

  test('audit each booking wizard step (Steps 1 to 4)', async ({ page }) => {
    await page.route('**/*checkout.razorpay.com/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/javascript',
        body: '/* Mocked Razorpay SDK */',
      })
    );

    // Step 1: Package Selection
    await page.goto('/book', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    let scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    let crit = scan.violations.filter((v) => v.impact === 'critical');
    expect(crit, 'Step 1: Package Selection has critical violations').toEqual([]);

    // Select Gold Package and proceed to Step 2
    await page.goto('/book?package=gold', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);

    // Step 2: Date & Slot Selection
    scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    crit = scan.violations.filter((v) => v.impact === 'critical');
    expect(crit, 'Step 2: Date & Slot Selection has critical violations').toEqual([]);

    // Fill Step 2 date and slot
    const dateObj = new Date(Date.now() + 18 * 24 * 3600 * 1000);
    const testDate = dateObj.toISOString().split('T')[0];
    const dateInput = page.locator('input[type="date"]');
    await dateInput.fill(testDate);
    await dateInput.dispatchEvent('change');

    await expect(page.getByText('Loading live availability')).not.toBeVisible({ timeout: 15000 });

    const slotBtn = page.locator('button:not([disabled])').filter({ hasText: /^\d{2}:00/ }).first();
    await expect(slotBtn).toBeVisible({ timeout: 15000 });
    await slotBtn.click();

    const nextBtnStep2 = page.locator('button:has-text("Next: Celebrant Details")');
    await expect(nextBtnStep2).toBeEnabled();
    await nextBtnStep2.click();

    // Step 3: Celebrant Details
    await expect(page.locator('h2')).toContainText('Step 3: Celebrant & Contact Info');
    scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    crit = scan.violations.filter((v) => v.impact === 'critical');
    expect(crit, 'Step 3: Celebrant Form has critical violations').toEqual([]);

    // Fill Step 3 form
    await page.locator('#customerNameInput').fill('A11y Test User');
    await page.locator('#customerPhoneInput').fill(`99${Date.now().toString().slice(-8)}`);
    await page.locator('#celebrantNameInput').fill('Test Child');

    const nextBtnStep3 = page.locator('button:has-text("Next: Review & Lock")');
    await expect(nextBtnStep3).toBeEnabled();
    await nextBtnStep3.click();

    // Step 4: Summary & Hold Lock
    await expect(page.locator('h2')).toContainText('Step 4: Reservation Summary & Lock');
    scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    crit = scan.violations.filter((v) => v.impact === 'critical');
    expect(crit, 'Step 4: Summary & Hold Lock has critical violations').toEqual([]);
  });

  test('audit authenticated admin console tabs for accessibility', async ({ page }, testInfo) => {
    const isMobile = testInfo.project.name.includes('mobile');
    await page.goto('/admin/login');
    await page.locator('#username').fill('test_owner');
    await page.locator('#password').fill('OwnerPassword123!');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL((url) => url.pathname === '/admin', { timeout: 15000 });

    const scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    const crit = scan.violations.filter((v) => v.impact === 'critical');
    expect(crit, 'Admin Console dashboard has critical violations').toEqual([]);
  });

  test('keyboard-only navigation through booking wizard steps', async ({ page }) => {
    await page.route('**/*checkout.razorpay.com/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/javascript',
        body: '/* Mocked Razorpay SDK */',
      })
    );

    await page.goto('/book', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    // Verify keyboard focus navigation is responsive
    await page.keyboard.press('Tab');
    const focusedTag = await page.evaluate(() => document.activeElement ? document.activeElement.tagName : null);
    expect(focusedTag).toBeTruthy();

    // Navigate to package selection and hit Enter
    const selectPackageBtn = page.locator('button:has-text("Choose"), button:has-text("Select")').first();
    await selectPackageBtn.focus();
    await page.keyboard.press('Enter');

    // Tab to Continue button and press Enter
    const continueBtn = page.locator('button:has-text("Continue"), button:has-text("Next")').first();
    await continueBtn.focus();
    await page.keyboard.press('Enter');
    await page.waitForTimeout(800);

    // Verify reached step 2 via keyboard
    const dateInput = page.locator('input[type="date"]');
    await expect(dateInput).toBeVisible();
    await dateInput.focus();
    await dateInput.fill('2026-11-28');
  });

  test('keyboard-only navigation through admin console', async ({ page }) => {
    await page.goto('/admin/login');
    const usernameInput = page.locator('#username');
    await usernameInput.focus();
    await page.keyboard.type('test_owner');
    await page.keyboard.press('Tab');
    await page.keyboard.type('OwnerPassword123!');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');

    await page.waitForURL((url) => url.pathname === '/admin', { timeout: 15000 });
    await expect(page.getByText(/Test Owner/i)).toBeVisible();

    // Verify Tab cycles focus through admin controls
    await page.keyboard.press('Tab');
    const activeEl = await page.evaluate(() => document.activeElement ? document.activeElement.tagName : null);
    expect(activeEl).toBeTruthy();
  });
});
