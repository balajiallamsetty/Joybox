import fs from 'node:fs';
import path from 'node:path';
import { test, expect } from '@playwright/test';

test.use({ trace: 'off', screenshot: 'off', video: 'off' });
import AxeBuilder from '@axe-core/playwright';
import { collectPageContrast, contrastRatio, hex, summarize } from './contrastMeasure.js';

const VIEWPORTS = [
  { name: 'mobile-390', width: 390, height: 844 },
  { name: 'desktop-1440', width: 1440, height: 900 },
];

const ALL_PAGES = [
  '/',
  '/packages',
  '/booking',
  '/gallery',
  '/contact',
  '/terms',
  '/privacy',
  '/refund-policy',
  '/admin/login',
  '/mobile-booking',
  '/booking-status',
  '/this-route-does-not-exist',
];

const routeFilter = (process.env.CONTRAST_ROUTES || '').split(',').map((item) => item.trim()).filter(Boolean);
const PAGES = routeFilter.length ? ALL_PAGES.filter((route) => routeFilter.includes(route)) : ALL_PAGES;

async function revealValidation(page, route) {
  if (route === '/contact') {
    const submit = page.getByRole('button', { name: /send|submit|inquire|request/i });
    if (await submit.count()) await submit.first().click().catch(() => {});
  }
  if (route === '/admin/login') {
    const submit = page.getByRole('button', { name: /sign in|log in|login/i });
    if (await submit.count()) await submit.first().click().catch(() => {});
  }
  if (route === '/booking') {
    const next = page.getByRole('button', { name: /continue|next|date & slot/i });
    if (await next.count()) await next.first().click().catch(() => {});
  }
  await page.waitForTimeout(200);
}

async function exerciseInteractiveEdgeStates(page, viewport, route, meta) {
  const edgeRows = [];

  // 1. Language switcher open / hovered
  const langSwitch = page.locator('[data-testid="language-switch"]');
  if (await langSwitch.count() && await langSwitch.first().isVisible().catch(() => false)) {
    const teluguBtn = langSwitch.locator('button', { hasText: /తెలుగు/i }).first();
    if (await teluguBtn.count()) {
      await teluguBtn.hover().catch(() => {});
      await page.waitForTimeout(100);
      edgeRows.push(...await collectPageContrast(page, { ...meta, state: 'lang-hover' }));
    }
  }

  // 2. Mobile hamburger menu open state
  if (viewport.name === 'mobile-390') {
    const menuBtn = page.locator('button[aria-label*="menu" i], button:has(.material-symbols-outlined:has-text("menu"))').first();
    if (await menuBtn.count() && await menuBtn.isVisible().catch(() => false)) {
      await menuBtn.click().catch(() => {});
      await page.waitForTimeout(300);
      edgeRows.push(...await collectPageContrast(page, { ...meta, state: 'mobile-menu-open' }));
      const closeBtn = page.locator('button[aria-label*="close" i], button:has(.material-symbols-outlined:has-text("close"))').first();
      if (await closeBtn.count()) {
        await closeBtn.click().catch(() => {});
      } else {
        await menuBtn.click().catch(() => {});
      }
      await page.waitForTimeout(200);
    }
  }

  // 3. Modals, Alerts, Dialogs, Toasts
  const dialogs = page.locator('[role="dialog"], [role="alert"], [role="status"], .toast, .modal');
  if (await dialogs.count()) {
    edgeRows.push(...await collectPageContrast(page, { ...meta, state: 'dialogs' }));
  }

  return edgeRows;
}

async function readControlContrast(page, locator) {
  return locator.evaluate((el) => {
    const parse = (value) => {
      const match = String(value || '').match(/rgba?\(([^)]+)\)/);
      if (!match) return null;
      const parts = match[1].split(',').map((part) => Number.parseFloat(part.trim()));
      return { r: parts[0], g: parts[1], b: parts[2], a: parts[3] ?? 1 };
    };
    const style = getComputedStyle(el);
    let node = el;
    let bg = null;
    let complex = false;
    while (node) {
      const nodeStyle = getComputedStyle(node);
      if (nodeStyle.backgroundImage && nodeStyle.backgroundImage !== 'none') {
        complex = true;
        break;
      }
      const color = parse(nodeStyle.backgroundColor);
      if (color && color.a >= 0.99) {
        bg = color;
        break;
      }
      node = node.parentElement;
    }
    const fg = parse(style.color);
    return {
      text: (el.innerText || el.getAttribute('placeholder') || el.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim().slice(0, 80),
      className: String(el.className || '').slice(0, 180),
      fg,
      bg,
      complex,
      fontSize: Number.parseFloat(style.fontSize || '16'),
      fontWeight: Number.parseInt(style.fontWeight || '400', 10),
      disabled: Boolean(el.disabled || el.getAttribute('aria-disabled') === 'true'),
    };
  });
}

function rowFromControl(sample, meta) {
  if (!sample || !sample.fg || !sample.bg || sample.complex) return null;
  const large = sample.fontSize >= 24 || (sample.fontSize >= 18.66 && sample.fontWeight >= 700);
  const threshold = large ? 3 : 4.5;
  const ratio = contrastRatio(sample.fg, sample.bg);
  return {
    ...meta,
    kind: 'control',
    text: sample.text,
    className: sample.className,
    tag: 'control',
    selector: '',
    fg: hex(sample.fg),
    bg: hex(sample.bg),
    ratio: Math.round(ratio * 100) / 100,
    threshold,
    pass: ratio + 0.05 >= threshold,
    fontSize: sample.fontSize,
    complex: false,
  };
}

async function exerciseStates(page, meta) {
  const rows = [];
  await page.evaluate(() => {
    window.__contrastBlock = (event) => {
      event.preventDefault();
      event.stopPropagation();
    };
    document.addEventListener('click', window.__contrastBlock, true);
  });
  const controls = page.locator('a, button, input, textarea, select, [role="button"]');
  const count = await controls.count();
  for (let i = 0; i < count; i += 1) {
    const control = controls.nth(i);
    if (!(await control.isVisible().catch(() => false))) continue;
    const className = await control.getAttribute('class').catch(() => '');
    if (!className || !/hover:|focus:|active:/.test(className)) continue;
    await control.scrollIntoViewIfNeeded().catch(() => {});
    await control.hover({ force: true }).catch(() => {});
    await page.waitForTimeout(350);
    rows.push(rowFromControl(await readControlContrast(page, control), { ...meta, state: 'hover' }));
    await control.focus().catch(() => {});
    await page.waitForTimeout(200);
    rows.push(rowFromControl(await readControlContrast(page, control), { ...meta, state: 'focus' }));
    const box = await control.boundingBox();
    if (box && box.y >= 70 && box.height > 0) {
      await page.evaluate(() => {
        document.addEventListener('click', (event) => event.preventDefault(), { capture: true, once: true });
      });
      await page.mouse.move(box.x + Math.min(4, box.width / 2), box.y + Math.min(4, box.height / 2));
      await page.mouse.down();
      await page.waitForTimeout(200);
      rows.push(rowFromControl(await readControlContrast(page, control), { ...meta, state: 'active' }));
      await page.mouse.up();
    }
  }
  const disabled = page.locator(':disabled, [aria-disabled="true"]');
  const disabledCount = await disabled.count();
  for (let i = 0; i < disabledCount; i += 1) {
    const control = disabled.nth(i);
    if (!(await control.isVisible().catch(() => false))) continue;
    rows.push(rowFromControl(await readControlContrast(page, control), { ...meta, state: 'disabled' }));
  }
  await page.evaluate(() => {
    if (window.__contrastBlock) document.removeEventListener('click', window.__contrastBlock, true);
  });
  await page.mouse.up().catch(() => {});
  await page.mouse.move(1, 1);
  return rows.filter(Boolean);
}

test('rendered contrast stays at or above WCAG thresholds', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop-chromium', '390 and 1440 are measured inside this test');
  test.setTimeout(600000);

  const phase = process.env.CONTRAST_AUDIT_PHASE || 'guard';
  const all = [];

  for (const viewport of VIEWPORTS) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const route of PAGES) {
      await page.goto(route, { waitUntil: 'domcontentloaded' });
      await page.mouse.up().catch(() => {});
      await page.mouse.move(1, 1);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(400);
      const meta = { viewport: viewport.name, route, state: 'rest' };
      all.push(...await collectPageContrast(page, meta));
      await page.mouse.move(1, 1);
      await page.evaluate(() => {
        window.scrollTo(0, 0);
        document.getAnimations().forEach((animation) => {
          const iterations = animation.effect && animation.effect.getTiming().iterations;
          if (iterations === Infinity) return;
          try {
            animation.finish();
          } catch {
            /* A spinner or unfinished effect can reject finish(). */
          }
        });
      });
      await page.waitForTimeout(400);

      const axe = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze();
      for (const violation of axe.violations) {
        for (const node of violation.nodes) {
          all.push({
            ...meta,
            state: 'axe',
            kind: 'axe',
            text: `${(node.html || '').slice(0, 80)} ${(node.failureSummary || '').slice(0, 180)}`,
            className: (node.target || []).join(' '),
            tag: 'axe',
            selector: (node.target || []).join(' '),
            fg: 'axe',
            bg: 'axe',
            ratio: 0,
            threshold: 4.5,
            pass: false,
            fontSize: 0,
            complex: false,
          });
        }
      }

      await revealValidation(page, route);
      all.push(...await collectPageContrast(page, { ...meta, state: 'validation' }));
      all.push(...await exerciseInteractiveEdgeStates(page, viewport, route, meta));
      if (viewport.name === 'desktop-1440') {
        all.push(...await exerciseStates(page, meta));
      }
    }
  }

  const measured = all.filter((row) => row.kind !== 'axe');
  const axeFailures = all.filter((row) => row.kind === 'axe');
  const summary = summarize(measured);
  const outDir = path.resolve(process.cwd(), '..', 'docs', 'contrast-audit');
  fs.mkdirSync(outDir, { recursive: true });
  const payload = {
    phase,
    pairsChecked: summary.pairsChecked,
    failures: summary.failures.length,
    passes: summary.passes,
    worst: summary.worst,
    axeFailures: axeFailures.length,
    axeSample: axeFailures.slice(0, 20),
    failureSample: summary.failures.slice(0, 120),
  };
  fs.writeFileSync(path.join(outDir, `${phase}-summary.json`), JSON.stringify(payload, null, 2));
  fs.writeFileSync(path.join(outDir, `${phase}-failures.json`), JSON.stringify(summary.failures, null, 2));
  console.log(`CONTRAST ${phase} pairs=${payload.pairsChecked} failures=${payload.failures} axe=${axeFailures.length}`);
  summary.worst.forEach((row, index) => {
    console.log(
      `WORST ${index + 1} ${row.ratio}:1 ${row.fg} on ${row.bg} ${row.route} ${row.viewport} ${row.state} ${row.kind} ${row.text}`
    );
  });

  if (phase === 'before') {
    const shotDir = path.join(outDir, 'before');
    fs.mkdirSync(shotDir, { recursive: true });
    for (let i = 0; i < summary.worst.length; i += 1) {
      const row = summary.worst[i];
      await page.setViewportSize(row.viewport === 'mobile-390' ? { width: 390, height: 844 } : { width: 1440, height: 900 });
      await page.goto(row.route, { waitUntil: 'domcontentloaded' });
      const locator = row.selector ? page.locator(row.selector).first() : page.getByText(row.text, { exact: false }).first();
      if (await locator.count()) {
        await locator.scrollIntoViewIfNeeded().catch(() => {});
        await locator.screenshot({ path: path.join(shotDir, `worst-${i + 1}.png`) }).catch(() => {});
      }
    }
    return;
  }

  expect(axeFailures, 'axe color-contrast violations').toEqual([]);
  expect(summary.failures, JSON.stringify(summary.worst, null, 2)).toEqual([]);
});
