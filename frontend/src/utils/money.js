/**
 * Money and Currency Utility Functions for Joybox Party Room
 * Standardizes INR formatting, minor units (paise), tax calculation, and balance computations.
 */

export function toRupees(minorUnits = 0) {
  const minor = Number(minorUnits) || 0;
  return minor / 100.0;
}

export function toMinorUnits(rupees = 0) {
  const r = Number(rupees) || 0;
  return Math.round(r * 100);
}

export function formatRupees(amount, isMinor = false) {
  const rupees = isMinor ? toRupees(amount) : Number(amount) || 0;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
    minimumFractionDigits: rupees % 1 === 0 ? 0 : 2,
  }).format(rupees);
}

export function calculateBalance(totalAmountMinor = 0, advancePaidMinor = 0) {
  const balanceMinor = Math.max(0, (Number(totalAmountMinor) || 0) - (Number(advancePaidMinor) || 0));
  return {
    balanceMinor,
    balanceRupees: toRupees(balanceMinor),
  };
}

export function calculateGst(taxableAmountMinor = 0, gstRatePercent = 18.0) {
  const taxable = Number(taxableAmountMinor) || 0;
  const rate = Number(gstRatePercent) || 0;
  const taxAmountMinor = Math.round(taxable * (rate / 100.0));
  const totalWithTaxMinor = taxable + taxAmountMinor;
  return {
    taxableAmountMinor: taxable,
    taxableRupees: toRupees(taxable),
    taxRatePercent: rate,
    taxAmountMinor,
    taxAmountRupees: toRupees(taxAmountMinor),
    totalWithTaxMinor,
    totalWithTaxRupees: toRupees(totalWithTaxMinor),
  };
}

export function computeLineItemsTotal(lineItems = []) {
  if (!Array.isArray(lineItems)) return 0;
  return lineItems.reduce((acc, item) => acc + (Number(item?.amountMinor) || 0), 0);
}
