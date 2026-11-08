function formatTo12Hour(time24) {
  if (!time24) return '';
  const [hourStr, minStr] = time24.split(':');
  let hour = parseInt(hourStr, 10);
  const ampm = hour >= 12 ? 'PM' : 'AM';
  hour = hour % 12 || 12;
  return `${hour}:${minStr || '00'} ${ampm}`;
}

const openTime = import.meta?.env?.VITE_OPENING_TIME || '09:00';
const closeTime = import.meta?.env?.VITE_CLOSING_TIME || '22:00';

export const VENUE_CONFIG = {
  openingTime: openTime,
  closingTime: closeTime,
  bufferMinutesMin: 30,
  bufferMinutesMax: 60,
  durationHoursMin: 1,
  durationHoursMax: 6,
  displayHours: `${formatTo12Hour(openTime)} – ${formatTo12Hour(closeTime)}`,
  hostName: import.meta?.env?.VITE_HOST_NAME || 'Kiran Kumar',
  whatsappNumber: import.meta?.env?.VITE_WHATSAPP_NUMBER || '917842704429',
  contactPhone: '+91 78427 04429',
  address: 'Beside Durga Mart, Vadlamudi, Guntur, Andhra Pradesh',
  paymentsEnabled: import.meta?.env?.VITE_PAYMENTS_ENABLED === 'true',
};

export const BOOKINGS_OPEN = false;
