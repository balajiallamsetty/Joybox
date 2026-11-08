"""
PII Scrubbing and Structured Logging Utilities for Joybox Party Room.
Ensures phone numbers, email addresses, and payment tokens are redacted
before being persisted to standard application logs.
"""

import re
import logging

# Regex patterns for sensitive PII
PHONE_REGEX = re.compile(r'(?:\+?91[\-\s]?)?([6-9]\d{5})(\d{4})\b')
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
CARD_REGEX = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
RAZORPAY_SECRET_REGEX = re.compile(r'(rzp_(?:test|live)_[A-Za-z0-9]{14})')

def scrub_pii(text: str) -> str:
    """Replaces sensitive customer PII and credential fragments in log text."""
    if not isinstance(text, str):
        text = str(text)

    # Redact Indian mobile numbers: keep only last 4 digits (e.g. ****1234)
    def _mask_phone(match):
        last4 = match.group(2)
        return f"****{last4}"

    text = PHONE_REGEX.sub(_mask_phone, text)

    # Redact email addresses (e.g. [REDACTED_EMAIL])
    text = EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)

    # Redact potential credit card numbers
    text = CARD_REGEX.sub("[REDACTED_CARD]", text)

    # Mask any inadvertent Razorpay key printouts
    text = RAZORPAY_SECRET_REGEX.sub("rzp_***_REDACTED", text)

    return text

class PIIScrubbingFilter(logging.Filter):
    """Logging filter that scrubs customer PII and secrets from all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = scrub_pii(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: scrub_pii(v) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(scrub_pii(a) if isinstance(a, str) else a for a in record.args)
        return True
