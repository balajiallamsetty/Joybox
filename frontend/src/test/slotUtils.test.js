import { describe, it, expect } from 'vitest';
import {
  computeSlotBufferEnd,
  generateOperatingSlots,
  categorizeSlots,
  getSlotStatusDisplay,
} from '../utils/slots.js';

describe('Frontend Slot & Buffer Utilities', () => {
  it('computes slot buffer end window with 30-minute default cushion', () => {
    // 09:00 start, 2 hours celebration -> event ends 11:00 -> buffer ends 11:30
    expect(computeSlotBufferEnd('09:00', 2, 30)).toBe('11:30');

    // 18:00 start, 3 hours celebration -> event ends 21:00 -> buffer ends 21:30
    expect(computeSlotBufferEnd('18:00', 3, 30)).toBe('21:30');
  });

  it('generates operating slots strictly within 09:00 - 22:00 operating envelope', () => {
    // For 2-hour duration, max start hour is 22 - 2 = 20:00 (ends at 22:00)
    const slots = generateOperatingSlots(9, 22, 2);
    expect(slots.length).toBe(12); // 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    expect(slots[0].startTime).toBe('09:00');
    expect(slots[0].endTime).toBe('11:00');
    expect(slots[slots.length - 1].startTime).toBe('20:00');
    expect(slots[slots.length - 1].endTime).toBe('22:00');
  });

  it('categorizes slots into available and unavailable collections', () => {
    const rawSlots = [
      { startTime: '09:00', available: true },
      { startTime: '10:00', available: false, unavailableReason: 'booked' },
      { startTime: '11:00', available: false, unavailableReason: 'buffer' },
      { startTime: '12:00', available: true },
    ];
    const { available, unavailable } = categorizeSlots(rawSlots);
    expect(available.length).toBe(2);
    expect(unavailable.length).toBe(2);
  });

  it('maps unavailable reasons to friendly user-facing labels', () => {
    expect(getSlotStatusDisplay({ available: true })).toBe('Available');
    expect(getSlotStatusDisplay({ available: false, unavailableReason: 'past' })).toBe('Past Time');
    expect(getSlotStatusDisplay({ available: false, unavailableReason: 'booked' })).toBe('Booked');
    expect(getSlotStatusDisplay({ available: false, unavailableReason: 'hold' })).toBe('Reserved / Temporary Hold');
    expect(getSlotStatusDisplay({ available: false, unavailableReason: 'buffer' })).toBe('30-Min Cleaning & Buffer');
    expect(getSlotStatusDisplay(null)).toBe('Unknown');
  });
});
