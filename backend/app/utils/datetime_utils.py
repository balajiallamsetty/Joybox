from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re

try:
    IST_TZ = ZoneInfo("Asia/Kolkata")
except ZoneInfoNotFoundError as _e:
    raise RuntimeError(
        "CRITICAL ERROR: Timezone 'Asia/Kolkata' could not be loaded. "
        "On Windows, ensure 'tzdata' is installed in the Python environment: pip install tzdata"
    ) from _e

UTC_TZ = timezone.utc

def get_ist_timezone():
    return IST_TZ

def now_utc() -> datetime:
    return datetime.now(UTC_TZ)

def now_ist() -> datetime:
    return datetime.now(IST_TZ)

def parse_ist_datetime(date_str: str, time_str: str) -> datetime:
    """
    Parses date (YYYY-MM-DD) and time (HH:MM or H:MM) as Asia/Kolkata local time.
    Returns timezone-aware datetime in IST.
    """
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str.strip()):
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.")
    
    time_clean = time_str.strip()
    if not re.match(r"^\d{1,2}:\d{2}$", time_clean):
        raise ValueError(f"Invalid time format '{time_str}'. Expected HH:MM.")

    dt_str = f"{date_str.strip()} {time_clean}"
    try:
        naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError(f"Invalid date or time value: {exc}")

    return naive.replace(tzinfo=IST_TZ)

def to_utc(dt: datetime) -> datetime:
    """Converts a timezone-aware datetime to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(UTC_TZ)

def ensure_utc(dt: datetime) -> datetime:
    """Ensures a datetime is timezone-aware in UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(UTC_TZ)

def to_ist(dt: datetime) -> datetime:
    """Converts a timezone-aware datetime to IST."""
    if dt.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware.")
    return dt.astimezone(IST_TZ)

def format_ist_time(dt: datetime) -> str:
    ist_dt = to_ist(dt)
    return ist_dt.strftime("%I:%M %p")

def format_ist_date(dt: datetime) -> str:
    ist_dt = to_ist(dt)
    return ist_dt.strftime("%Y-%m-%d")

def format_ist_display(dt: datetime) -> str:
    ist_dt = to_ist(dt)
    return ist_dt.strftime("%a, %b %d, %Y %I:%M %p")

def get_ist_period_key(dt: datetime = None) -> str:
    """Returns 'YYYY-MM' period key in Asia/Kolkata timezone."""
    ist_dt = to_ist(dt or now_utc())
    return ist_dt.strftime("%Y-%m")

def generate_slot_claim_intervals(
    start_utc: datetime,
    end_utc: datetime,
    buffer_minutes: int = 30,
    slot_unit_minutes: int = 30
) -> list[dict]:
    """
    Generates aligned slot intervals for atomic reservation in slotClaims collection.
    Covers the event duration [start_utc, end_utc) plus the post-event buffer [end_utc, end_utc + buffer_minutes).
    """
    intervals = []
    unit = timedelta(minutes=slot_unit_minutes)

    # 1. Event duration slots
    curr = start_utc
    while curr < end_utc:
        slot_end = curr + unit
        intervals.append({
            "slotStart": curr,
            "slotEnd": slot_end,
            "isBuffer": False
        })
        curr = slot_end

    # 2. Buffer slots
    buffer_end = end_utc + timedelta(minutes=buffer_minutes)
    while curr < buffer_end:
        slot_end = curr + unit
        intervals.append({
            "slotStart": curr,
            "slotEnd": slot_end,
            "isBuffer": True
        })
        curr = slot_end

    return intervals

def _get_cfg_val(config, key, default=None):
    if hasattr(config, key):
        val = getattr(config, key)
        if val is not None:
            return val
    if hasattr(config, "get"):
        val = config.get(key)
        if val is not None:
            return val
    return default

def validate_booking_window(
    date_str: str,
    time_str: str,
    duration_hours: int,
    config
) -> tuple[datetime, datetime, datetime]:
    """
    Validates business constraints on requested celebration time window:
    - Min and max duration
    - Whole hours on the hour
    - Between OPENING_HOUR_IST (09:00) and CLOSING_HOUR_IST (22:00)
    - Not in the past
    Returns (start_utc, end_utc, buffer_end_utc).
    """
    min_dur = _get_cfg_val(config, "MIN_DURATION_HOURS", 1)
    max_dur = _get_cfg_val(config, "MAX_DURATION_HOURS", 6)
    opening_hour = _get_cfg_val(config, "OPENING_HOUR_IST", 9)
    closing_hour = _get_cfg_val(config, "CLOSING_HOUR_IST", 22)
    buffer_min = _get_cfg_val(config, "BUFFER_MINUTES", 30)

    if not isinstance(duration_hours, int) or duration_hours < min_dur or duration_hours > max_dur:
        raise ValueError(
            f"Duration must be an integer between {min_dur} and {max_dur} hours."
        )

    start_ist = parse_ist_datetime(date_str, time_str)
    now = now_ist()

    # Reject past bookings
    if start_ist < now:
        raise ValueError(f"Requested start time {start_ist.strftime('%Y-%m-%d %H:%M')} IST is in the past.")

    # Reject bookings beyond max advance booking window
    max_advance_days = _get_cfg_val(config, "MAX_ADVANCE_BOOKING_DAYS", 90)
    if start_ist > now + timedelta(days=max_advance_days):
        raise ValueError(f"Bookings cannot be made more than {max_advance_days} days in advance.")

    # Must be on the hour
    if start_ist.minute != 0:
        raise ValueError("Booking start time must align to the top of the hour (e.g. 09:00, 10:00).")

    # Check opening hour
    if start_ist.hour < opening_hour:
        raise ValueError(f"Venue opens at {opening_hour:02d}:00 AM IST. Requested start {start_ist.strftime('%H:%M')} is too early.")

    end_ist = start_ist + timedelta(hours=duration_hours)

    # Check closing hour
    # Event party must end by closing_hour (22:00)
    closing_dt = start_ist.replace(hour=closing_hour, minute=0, second=0, microsecond=0)
    if end_ist > closing_dt:
        raise ValueError(
            f"Party duration extends to {end_ist.strftime('%I:%M %p')}, past venue closing time of {closing_hour:02d}:00 IST (10:00 PM)."
        )

    buffer_end_ist = end_ist + timedelta(minutes=buffer_min)

    start_utc = to_utc(start_ist)
    end_utc = to_utc(end_ist)
    buffer_end_utc = to_utc(buffer_end_ist)

    return start_utc, end_utc, buffer_end_utc
