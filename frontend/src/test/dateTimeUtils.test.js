import { describe, it, expect } from 'vitest';
import {
  parseTimeString,
  formatSlotTime,
  calculateEndTime,
  formatDateToIsoString,
  getMinBookingDate,
  getMaxBookingDate,
  isDateAllowed,
} from '../utils/dateTime.js';

describe('Frontend Date & Time Utilities', () => {
  it('parses military time strings into hours and minutes', () => {
    expect(parseTimeString('09:00')).toEqual({ hour: 9, minute: 0 });
    expect(parseTimeString('18:30')).toEqual({ hour: 18, minute: 30 });
    expect(parseTimeString('invalid')).toEqual({ hour: 0, minute: 0 });
  });

  it('formats slot military times to 12-hour AM/PM representations', () => {
    expect(formatSlotTime('09:00')).toBe('09:00 AM');
    expect(formatSlotTime('12:00')).toBe('12:00 PM');
    expect(formatSlotTime('14:00')).toBe('02:00 PM');
    expect(formatSlotTime('18:00')).toBe('06:00 PM');
    expect(formatSlotTime('21:30')).toBe('09:30 PM');
  });

  it('calculates event end times given duration hours', () => {
    expect(calculateEndTime('09:00', 2)).toBe('11:00');
    expect(calculateEndTime('18:00', 3)).toBe('21:00');
    expect(calculateEndTime('19:00', 1)).toBe('20:00');
  });

  it('computes minimum and maximum allowed booking calendar dates (90-day window)', () => {
    const fixedNow = new Date('2026-11-01T10:00:00Z');
    const minDate = getMinBookingDate(fixedNow);
    const maxDate = getMaxBookingDate(fixedNow, 90);

    expect(minDate).toBe('2026-11-01');
    expect(maxDate).toBe('2027-01-30');

    // Day 0 (today) is allowed
    expect(isDateAllowed('2026-11-01', fixedNow, 90)).toBe(true);

    // Day 45 (within range) is allowed
    expect(isDateAllowed('2026-12-15', fixedNow, 90)).toBe(true);

    // Day 90 (boundary) is allowed
    expect(isDateAllowed('2027-01-30', fixedNow, 90)).toBe(true);

    // Day 91 (beyond maximum advance window) is rejected
    expect(isDateAllowed('2027-01-31', fixedNow, 90)).toBe(false);

    // Past date is rejected
    expect(isDateAllowed('2026-10-31', fixedNow, 90)).toBe(false);
  });

  it('formats dates to ISO YYYY-MM-DD string', () => {
    const d = new Date(2026, 10, 8); // November 8, 2026
    expect(formatDateToIsoString(d)).toBe('2026-11-08');
  });
});
