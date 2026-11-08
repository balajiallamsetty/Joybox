/**
 * Date and Time Utilities for Joybox Party Room
 * Operates on IST calendar representations, slot windows, and advance limits.
 */

export function parseTimeString(timeStr = '') {
  const parts = String(timeStr).split(':');
  if (parts.length < 2) return { hour: 0, minute: 0 };
  const hour = parseInt(parts[0], 10);
  const minute = parseInt(parts[1], 10);
  return {
    hour: isNaN(hour) ? 0 : hour,
    minute: isNaN(minute) ? 0 : minute,
  };
}

export function formatSlotTime(timeStr = '') {
  const { hour, minute } = parseTimeString(timeStr);
  const period = hour >= 12 ? 'PM' : 'AM';
  const displayHour = hour % 12 === 0 ? 12 : hour % 12;
  const padHour = String(displayHour).padStart(2, '0');
  const padMin = String(minute).padStart(2, '0');
  return `${padHour}:${padMin} ${period}`;
}

export function calculateEndTime(startTimeStr = '09:00', durationHours = 2) {
  const { hour, minute } = parseTimeString(startTimeStr);
  const endHour = hour + Number(durationHours);
  const padHour = String(endHour).padStart(2, '0');
  const padMin = String(minute).padStart(2, '0');
  return `${padHour}:${padMin}`;
}

export function formatDateToIsoString(d = new Date()) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function getMinBookingDate(referenceDate = new Date()) {
  return formatDateToIsoString(referenceDate);
}

export function getMaxBookingDate(referenceDate = new Date(), maxAdvanceDays = 90) {
  const d = new Date(referenceDate.getTime());
  d.setDate(d.getDate() + Number(maxAdvanceDays));
  return formatDateToIsoString(d);
}

export function isDateAllowed(dateStr, referenceDate = new Date(), maxAdvanceDays = 90) {
  if (!dateStr || typeof dateStr !== 'string') return false;
  const minDate = getMinBookingDate(referenceDate);
  const maxDate = getMaxBookingDate(referenceDate, maxAdvanceDays);
  return dateStr >= minDate && dateStr <= maxDate;
}
