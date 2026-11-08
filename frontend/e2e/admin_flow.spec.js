import { test, expect } from '@playwright/test';

test.describe('Admin Operations Console & RBAC Journey', () => {
  test('unauthenticated visitor is redirected to login, invalid login fails, and valid owner login accesses all tabs', async ({ page }, testInfo) => {
    const isMobile = testInfo.project.name.includes('mobile');

    async function selectTab(tabText) {
      if (isMobile) {
        const hamburger = page.locator('button[aria-label="Toggle navigation menu"]');
        await hamburger.click();
        await page.waitForTimeout(300);
      }
      const tabBtn = page.locator(`button:has-text("${tabText}")`);
      await tabBtn.click();
    }

    // 1. Unauthenticated visitor accessing /admin must be redirected to /admin/login
    await page.goto('/admin');
    await expect(page).toHaveURL(/\/admin\/login/);
    await expect(page.locator('h1')).toContainText('Operations Console');

    // 2. Attempt login with bad credentials
    await page.locator('#username').fill('bad_admin');
    await page.locator('#password').fill('wrongpassword123');
    await page.locator('button[type="submit"]').click();

    // Verify invalid credentials error banner
    await expect(page.getByText('Invalid username or password.')).toBeVisible({ timeout: 10000 });

    // 3. Login with valid test owner credentials
    await page.locator('#username').fill('test_owner');
    await page.locator('#password').fill('OwnerPassword123!');
    await page.locator('button[type="submit"]').click();

    // Explicitly wait for navigation to /admin
    await page.waitForURL(url => url.pathname === '/admin', { timeout: 15000 });

    // Verify user role badge and display name
    await expect(page.getByText(/Test Owner/i)).toBeVisible();
    await expect(page.getByText(/owner/i).first()).toBeVisible();

    // 4. Tab Navigation Verification
    // Tab: Schedule & Bookings
    await selectTab('Schedule & Bookings');
    await expect(page.getByRole('heading', { name: /Bookings & Schedule/i })).toBeVisible();

    // Tab: Inquiries & Leads
    await selectTab('Inquiries & Leads');
    await expect(page.getByRole('heading', { name: /Customer Inquiries/i })).toBeVisible();

    // Tab: Hall Blocks & Slots
    await selectTab('Hall Blocks & Slots');
    await expect(page.getByRole('heading', { name: /Emergency Hall Blocks/i })).toBeVisible();

    // Tab: Audit Logs
    await selectTab('Audit Logs');
    await expect(page.getByRole('heading', { name: /System Audit Trail/i })).toBeVisible();

    // 5. Secure Logout
    const logoutBtn = page.locator('button:has-text("Sign Out")');
    await logoutBtn.first().click();

    // Verify returned to login page
    await expect(page).toHaveURL(/\/admin\/login/);
  });
});
