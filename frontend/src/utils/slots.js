/**
 * Slot Availability & Buffer Utilities for Joybox Party Room
 * Venue Rules: Operating window 09:00 - 22:00 IST, 30m buffer between bookings.
 */

import { parseTimeString, calculateEndTime } from './dateTime.js';

export function computeSlotBufferEnd(startTimeStr = '09:00', durationHours = 2, bufferMinutes = 30) {
  const { hour, minute } = parseTimeString(startTimeStr);
  const totalMinutes = hour * 60 + minute + (Number(durationHours) * 60) + Number(bufferMinutes);
  const endHour = Math.floor(totalMinutes / 60);
  const endMin = totalMinutes % 60;
  return `${String(endHour).padStart(2, '0')}:${String(endMin).padStart(2, '0')}`;
}

export function generateOperatingSlots(openingHour = 9, closingHour = 22, durationHours = 2) {
  const maxStartHour = closingHour - durationHours;
  const slots = [];
  for (let h = openingHour; h <= maxStartHour; h++) {
    const startStr = `${String(h).padStart(2, '0')}:00`;
    const endStr = calculateEndTime(startStr, durationHours);
    slots.push({
      startTime: startStr,
      endTime: endStr,
      available: true,
    });
  }
  return slots;
}

export function categorizeSlots(slots = []) {
  if (!Array.isArray(slots)) return { available: [], unavailable: [] };
  const available = [];
  const unavailable = [];
  for (const s of slots) {
    if (s.available) {
      available.push(s);
    } else {
      unavailable.push(s);
    }
  }
  return { available, unavailable };
}

export function getSlotStatusDisplay(slot) {
  if (!slot) return 'Unknown';
  if (slot.available) return 'Available';
  switch (slot.unavailableReason) {
    case 'past':
      return 'Past Time';
    case 'booked':
      return 'Booked';
    case 'hold':
      return 'Reserved / Temporary Hold';
    case 'buffer':
      return '30-Min Cleaning & Buffer';
    default:
      return 'Unavailable';
  }
}
