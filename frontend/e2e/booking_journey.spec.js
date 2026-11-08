import { test, expect } from '@playwright/test';

function getFutureDate(offset = 0) {
  const d = new Date();
  const dayOffset = 20 + ((Date.now() + offset) % 50);
  d.setDate(d.getDate() + dayOffset);
  return d.toISOString().split('T')[0];
}

function getUniquePhone() {
  return '98' + Math.floor(10000000 + Math.random() * 90000000);
}

test.describe('Matrix F: E2E Booking Journey & Contention', () => {
  test('Complete booking flow carries package=gold, verifies quote, and creates reservation', async ({ page }, testInfo) => {
    // Intercept external checkout CDN so test runs deterministically in offline/deferred environment
    await page.route('**/*checkout.razorpay.com/**', route => route.abort());

    const targetDate = testInfo.project.name.includes('mobile') ? getFutureDate(11) : getFutureDate(3);
    const testPhone = getUniquePhone();

    // 1. Visit wizard with package preselected
    await page.goto(`/book?package=gold`);

    // Verify Step 2 is active and Gold package is displayed
    await expect(page.locator('h2')).toContainText('Step 2: Choose Date & Time Slot');
    await expect(page.getByText(/Gold Package/i)).toBeVisible();

    // 2. Change celebration date
    const dateInput = page.locator('input[type="date"]');
    await dateInput.fill(targetDate);
    await dateInput.dispatchEvent('change');

    // Wait for slot loading indicator to disappear
    await expect(page.getByText('Loading live availability')).not.toBeVisible({ timeout: 15000 });

    // Dynamically pick the first available open slot
    const slotButton = page.locator('button:not([disabled])').filter({ hasText: /^\d{2}:00/ }).first();
    await expect(slotButton).toBeVisible({ timeout: 15000 });
    await slotButton.click();

    // 3. Advance to Step 3: Celebrant Info
    const nextBtnStep2 = page.locator('button:has-text("Next: Celebrant Details")');
    await expect(nextBtnStep2).toBeEnabled();
    await nextBtnStep2.click();

    await expect(page.locator('h2')).toContainText('Step 3: Celebrant & Contact Info');

    // Fill Celebrant & Contact Details with fresh unique phone
    await page.locator('input[placeholder="e.g. Priya"]').fill('Aarav Birthday');
    await page.locator('input[placeholder="e.g. Ravi Kumar"]').fill('Sneha Sharma');
    await page.locator('input[placeholder="e.g. 9876543210"]').fill(testPhone);

    // 4. Advance to Step 4: Review & Lock
    const nextBtnStep3 = page.locator('button:has-text("Next: Review & Lock")');
    await nextBtnStep3.click();

    await expect(page.locator('h2')).toContainText('Step 4: Reservation Summary & Lock');

    // Verify live server quote breakdown
    await expect(page.getByText('Total Payable:')).toBeVisible();
    await expect(page.locator('text=Total Payable:').locator('..')).toContainText('₹');

    // 5. Click Pay & Lock Slot to initiate reservation
    const payButton = page.locator('button:has-text("Pay & Lock Slot")');
    await expect(payButton).toBeEnabled();
    await payButton.click();

    // Assert booking created and redirected to booking status page
    await page.waitForURL(/\/booking\/JBX-/, { timeout: 25000 });
    expect(page.url()).toMatch(/\/booking\/JBX-\d{4}-\d{4}/);
    await expect(page.getByText(/JBX-\d{4}-\d{4}/)).toBeVisible();
  });

  test('Concurrent browser sessions: second user cannot select already booked slot', async ({ browser }, testInfo) => {
    const targetDate = testInfo.project.name.includes('mobile') ? getFutureDate(23) : getFutureDate(17);
    const testPhone = getUniquePhone();

    // Browser Context 1 (First Customer)
    const context1 = await browser.newContext();
    const page1 = await context1.newPage();
    await page1.route('**/*checkout.razorpay.com/**', route => route.abort());

    await page1.goto(`/book?package=gold`);
    await page1.locator('input[type="date"]').fill(targetDate);
    await page1.locator('input[type="date"]').dispatchEvent('change');
    await expect(page1.getByText('Loading live availability')).not.toBeVisible({ timeout: 15000 });

    // Dynamically select the first available open slot
    const slot1 = page1.locator('button:not([disabled])').filter({ hasText: /^\d{2}:00/ }).first();
    await expect(slot1).toBeVisible({ timeout: 15000 });
    const bookedTime = (await slot1.locator('span').first().textContent()).trim();
    await slot1.click();

    await page1.locator('button:has-text("Next: Celebrant Details")').click();
    await page1.locator('input[placeholder="e.g. Priya"]').fill('First User');
    await page1.locator('input[placeholder="e.g. Ravi Kumar"]').fill('First Customer');
    await page1.locator('input[placeholder="e.g. 9876543210"]').fill(testPhone);
    await page1.locator('button:has-text("Next: Review & Lock")').click();
    await page1.locator('button:has-text("Pay & Lock Slot")').click();
    await page1.waitForURL(/\/booking\/JBX-/, { timeout: 25000 });

    // Browser Context 2 (Second Customer trying the same slot on the same date)
    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    await page2.route('**/*checkout.razorpay.com/**', route => route.abort());

    await page2.goto(`/book?package=gold`);
    await page2.locator('input[type="date"]').fill(targetDate);
    await page2.locator('input[type="date"]').dispatchEvent('change');
    await expect(page2.getByText('Loading live availability')).not.toBeVisible({ timeout: 15000 });

    // The slot booked by User 1 must now be disabled / unavailable for User 2
    const slot2 = page2.locator('button').filter({ hasText: new RegExp(`^${bookedTime}`) });
    await expect(slot2).toBeVisible({ timeout: 15000 });
    await expect(slot2).toBeDisabled();

    await context1.close();
    await context2.close();
  });

  test('Date-scoped availability: slot booked on Date A remains available on Date B', async ({ page }, testInfo) => {
    await page.route('**/*checkout.razorpay.com/**', route => route.abort());

    const dateA = testInfo.project.name.includes('mobile') ? getFutureDate(31) : getFutureDate(35);
    const dateB = testInfo.project.name.includes('mobile') ? getFutureDate(32) : getFutureDate(36);
    const testPhone = getUniquePhone();

    // 1. Book slot on Date A
    await page.goto(`/book?package=basic`);
    await page.locator('input[type="date"]').fill(dateA);
    await page.locator('input[type="date"]').dispatchEvent('change');
    await expect(page.getByText('Loading live availability')).not.toBeVisible({ timeout: 15000 });

    const slotA = page.locator('button:not([disabled])').filter({ hasText: /^\d{2}:00/ }).first();
    await expect(slotA).toBeVisible({ timeout: 15000 });
    const slotTime = (await slotA.locator('span').first().textContent()).trim();
    await slotA.click();

    await page.locator('button:has-text("Next: Celebrant Details")').click();
    await page.locator('input[placeholder="e.g. Priya"]').fill('Date Test Celebrant');
    await page.locator('input[placeholder="e.g. Ravi Kumar"]').fill('Date Test Customer');
    await page.locator('input[placeholder="e.g. 9876543210"]').fill(testPhone);
    await page.locator('button:has-text("Next: Review & Lock")').click();
    await page.locator('button:has-text("Pay & Lock Slot")').click();
    await page.waitForURL(/\/booking\/JBX-/, { timeout: 25000 });

    // 2. Open wizard for Date B with identical slotTime -> must be enabled
    await page.goto(`/book?package=basic`);
    await page.locator('input[type="date"]').fill(dateB);
    await page.locator('input[type="date"]').dispatchEvent('change');
    await expect(page.getByText('Loading live availability')).not.toBeVisible({ timeout: 15000 });

    const slotOnDateB = page.locator('button').filter({ hasText: new RegExp(`^${slotTime}`) });
    await expect(slotOnDateB).toBeVisible({ timeout: 15000 });
    await expect(slotOnDateB).toBeEnabled();

    // 3. Return to Date A -> slotTime must be disabled
    await page.locator('input[type="date"]').fill(dateA);
    await page.locator('input[type="date"]').dispatchEvent('change');
    await expect(page.getByText('Loading live availability')).not.toBeVisible({ timeout: 15000 });

    const slotOnDateA = page.locator('button').filter({ hasText: new RegExp(`^${slotTime}`) });
    await expect(slotOnDateA).toBeVisible({ timeout: 15000 });
    await expect(slotOnDateA).toBeDisabled();
  });

  test('Cancellation journey: customer cancels active booking and releases slot back to calendar', async ({ page }, testInfo) => {
    await page.route('**/*checkout.razorpay.com/**', route => route.abort());

    // Setup dialog auto-acceptance for confirmation and prompt
    page.on('dialog', async (dialog) => {
      await dialog.accept('E2E test cancellation');
    });

    const targetDate = testInfo.project.name.includes('mobile') ? getFutureDate(41) : getFutureDate(45);
    const testPhone = getUniquePhone();

    // 1. Create a reservation
    await page.goto(`/book?package=basic`);
    await page.locator('input[type="date"]').fill(targetDate);
    await page.locator('input[type="date"]').dispatchEvent('change');
    await expect(page.getByText('Loading live availability')).not.toBeVisible({ timeout: 15000 });

    const slotBtn = page.locator('button:not([disabled])').filter({ hasText: /^\d{2}:00/ }).first();
    await expect(slotBtn).toBeVisible({ timeout: 15000 });
    const bookedTime = (await slotBtn.locator('span').first().textContent()).trim();
    await slotBtn.click();

    await page.locator('button:has-text("Next: Celebrant Details")').click();
    await page.locator('input[placeholder="e.g. Priya"]').fill('Cancel Test Celebrant');
    await page.locator('input[placeholder="e.g. Ravi Kumar"]').fill('Cancel Test Customer');
    await page.locator('input[placeholder="e.g. 9876543210"]').fill(testPhone);
    await page.locator('button:has-text("Next: Review & Lock")').click();
    await page.locator('button:has-text("Pay & Lock Slot")').click();
    await page.waitForURL(/\/booking\/JBX-/, { timeout: 25000 });

    // 2. Click Cancel Reservation on Status Page
    const cancelBtn = page.locator('button:has-text("Cancel Reservation")');
    await expect(cancelBtn).toBeVisible({ timeout: 15000 });
    await cancelBtn.click();

    // 3. Assert Cancelled Banner is displayed
    await expect(page.getByText('Booking Has Been Cancelled')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Reservation Cancelled')).toBeVisible();

    // 4. Return to wizard on targetDate -> slot must now be released and enabled
    await page.goto(`/book?package=basic`);
    await page.locator('input[type="date"]').fill(targetDate);
    await page.locator('input[type="date"]').dispatchEvent('change');
    await expect(page.getByText('Loading live availability')).not.toBeVisible({ timeout: 15000 });

    const releasedSlot = page.locator('button').filter({ hasText: new RegExp(`^${bookedTime}`) });
    await expect(releasedSlot).toBeVisible({ timeout: 15000 });
    await expect(releasedSlot).toBeEnabled();
  });
});
