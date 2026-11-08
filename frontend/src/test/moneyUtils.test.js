import { describe, it, expect } from 'vitest';
import {
  toRupees,
  toMinorUnits,
  formatRupees,
  calculateBalance,
  calculateGst,
  computeLineItemsTotal,
} from '../utils/money.js';

describe('Frontend Money Utilities', () => {
  it('converts minor units (paise) to rupees accurately', () => {
    expect(toRupees(100000)).toBe(1000.0);
    expect(toRupees(50050)).toBe(500.5);
    expect(toRupees(0)).toBe(0);
    expect(toRupees(null)).toBe(0);
  });

  it('converts rupees to minor units (paise) with round-half-up precision', () => {
    expect(toMinorUnits(1000)).toBe(100000);
    expect(toMinorUnits(500.5)).toBe(50050);
    expect(toMinorUnits(299.99)).toBe(29999);
    expect(toMinorUnits(0)).toBe(0);
  });

  it('formats rupees to Indian numbering standard string with ₹ symbol', () => {
    const formatted = formatRupees(1500);
    expect(formatted).toContain('1,500');
    expect(formatted).toContain('₹');

    const formattedMinor = formatRupees(150000, true);
    expect(formattedMinor).toContain('1,500');
  });

  it('calculates remaining balance due after token advance payment', () => {
    const { balanceMinor, balanceRupees } = calculateBalance(410000, 50000);
    expect(balanceMinor).toBe(360000);
    expect(balanceRupees).toBe(3600.0);

    // Overpayment or zero balance guard
    const zeroBalance = calculateBalance(50000, 50000);
    expect(zeroBalance.balanceMinor).toBe(0);
    expect(zeroBalance.balanceRupees).toBe(0);
  });

  it('calculates 18% GST with paise rounding and total computation', () => {
    // 3,000 INR = 300,000 paise. 18% of 300,000 = 54,000 paise (540 INR)
    const gstResult = calculateGst(300000, 18.0);
    expect(gstResult.taxableAmountMinor).toBe(300000);
    expect(gstResult.taxRatePercent).toBe(18.0);
    expect(gstResult.taxAmountMinor).toBe(54000);
    expect(gstResult.taxAmountRupees).toBe(540.0);
    expect(gstResult.totalWithTaxMinor).toBe(354000);
    expect(gstResult.totalWithTaxRupees).toBe(3540.0);

    // Flat rounding test on fractional paise
    // 999 INR = 99,900 paise. 18% = 17,982 paise
    const gstFraction = calculateGst(99900, 18.0);
    expect(gstFraction.taxAmountMinor).toBe(17982);
    expect(gstFraction.totalWithTaxMinor).toBe(117882);
  });

  it('computes line items total from structured quote items', () => {
    const lineItems = [
      { description: 'Gold Package (2 hrs)', amountMinor: 300000 },
      { description: 'Bubble Machine', amountMinor: 30000 },
      { description: 'Introductory Promotion', amountMinor: -30000 },
    ];
    expect(computeLineItemsTotal(lineItems)).toBe(300000);
    expect(computeLineItemsTotal([])).toBe(0);
  });
});
