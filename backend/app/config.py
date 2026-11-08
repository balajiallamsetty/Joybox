import os
from dotenv import load_dotenv

# Detect and reject legacy variable names early
_LEGACY_KEYS = ["MONGO_URI", "MONGO_TEST_URI", "MONGODB_URL"]
for _k in _LEGACY_KEYS:
    if os.getenv(_k):
        raise ValueError(
            f"CRITICAL CONFIG ERROR: Detected unsupported legacy environment variable '{_k}'. "
            f"Please update your .env to use the canonical name (e.g. 'MONGODB_URI' or 'MONGODB_TEST_DB')."
        )

# Load environment variables: backend/.env first, then root .env without overwriting existing vars
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)
load_dotenv(override=False)

# Check legacy keys again after loading .env
for _k in _LEGACY_KEYS:
    if os.getenv(_k):
        raise ValueError(
            f"CRITICAL CONFIG ERROR: Detected unsupported legacy environment variable '{_k}' in .env. "
            f"Please update your .env to use the canonical name (e.g. 'MONGODB_URI' or 'MONGODB_TEST_DB')."
        )

class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = FLASK_ENV.lower() == "development"
    TESTING = os.getenv("TESTING", "false").lower() in ("true", "1") or FLASK_ENV.lower() == "testing"
    PORT = int(os.getenv("PORT", 5000))
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    MONGODB_URI = os.getenv("MONGODB_URI", "")
    MONGODB_DB = os.getenv("MONGODB_DB", "joybox_party_room")
    MONGODB_TEST_DB = os.getenv("MONGODB_TEST_DB", "joybox_party_room_test")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-prod")
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    RAZORPAY_API_BASE = os.getenv("RAZORPAY_API_BASE", "https://api.razorpay.com/v1")
    PAYMENT_CURRENCY = "INR"
    HOLD_DURATION_MINUTES = int(os.getenv("HOLD_DURATION_MINUTES", 15)) # Reconciled default: 15 minutes hold TTL
    CHECKOUT_GRACE_MINUTES = int(os.getenv("CHECKOUT_GRACE_MINUTES", HOLD_DURATION_MINUTES))
    PAYMENT_WINDOW_EXTENSION_MINUTES = int(os.getenv("PAYMENT_WINDOW_EXTENSION_MINUTES", 15)) # Unconfirmed default
    MAX_PAYMENT_WINDOW_MINUTES = int(os.getenv("MAX_PAYMENT_WINDOW_MINUTES", 30))
    RECONCILIATION_AGE_MINUTES = int(os.getenv("RECONCILIATION_AGE_MINUTES", 15))
    GST_RATE_PERCENT = float(os.getenv("GST_RATE_PERCENT", 0.0)) # Unconfirmed default: 0% tax until GST registration

    PAYMENTS_ENABLED = os.getenv("PAYMENTS_ENABLED", "false").lower() in ("true", "1")
    BOOKINGS_OPEN = os.getenv("BOOKINGS_OPEN", "false").lower() in ("true", "1")
    ADVANCE_DEPOSIT_PAISE = int(os.getenv("ADVANCE_DEPOSIT_PAISE", 50000)) # Default ₹500 advance deposit

    # Mode Separation Guard: Refuse to start if live Razorpay key is configured in dev or test
    if (FLASK_ENV.lower() in ["development", "test"] or DEBUG) and RAZORPAY_KEY_ID.startswith("rzp_live_"):
        raise ValueError(
            f"CRITICAL CONFIG ERROR: Live Razorpay key '{RAZORPAY_KEY_ID[:12]}...' detected in '{FLASK_ENV}' environment. "
            "Development and testing environments must use test-mode keys ('rzp_test_...')."
        )

    # Refund & Cancellation Rules (Proposed defaults - marked UNCONFIRMED in docs/BUSINESS_RULES_REQUIRED.md)
    REFUND_WINDOW_FULL_HOURS = int(os.getenv("REFUND_WINDOW_FULL_HOURS", 48))      # > 48h before start: 100%
    REFUND_WINDOW_PARTIAL_HOURS = int(os.getenv("REFUND_WINDOW_PARTIAL_HOURS", 24)) # 24h-48h before start: 50%
    REFUND_WINDOW_PARTIAL_PERCENT = int(os.getenv("REFUND_WINDOW_PARTIAL_PERCENT", 50))
    REFUND_MIN_NOTICE_HOURS = int(os.getenv("REFUND_MIN_NOTICE_HOURS", 24))        # < 24h before start: 0%

    # Admin Auth & Session Management (Proposed defaults)
    ADMIN_SESSION_LIFETIME_HOURS = int(os.getenv("ADMIN_SESSION_LIFETIME_HOURS", 8))
    ADMIN_SESSION_IDLE_MINUTES = int(os.getenv("ADMIN_SESSION_IDLE_MINUTES", 30))
    ADMIN_COOKIE_NAME = os.getenv("ADMIN_COOKIE_NAME", "joybox_admin_session")
    ADMIN_COOKIE_SECURE = FLASK_ENV.lower() == "production"
    ADMIN_COOKIE_HTTPONLY = True
    ADMIN_COOKIE_SAMESITE = os.getenv("ADMIN_COOKIE_SAMESITE", "Lax")
    ADMIN_SESSION_COOKIE_NAME = ADMIN_COOKIE_NAME
    SESSION_COOKIE_SECURE = ADMIN_COOKIE_SECURE
    SESSION_COOKIE_SAMESITE = ADMIN_COOKIE_SAMESITE
    CSRF_HEADER_NAME = "X-CSRF-Token"
    TRUSTED_PROXIES = [p.strip() for p in os.getenv("TRUSTED_PROXIES", "127.0.0.1").split(",") if p.strip()]
    try:
        _raw_proxy = os.getenv("TRUSTED_PROXY_COUNT")
        TRUSTED_PROXY_COUNT = int(_raw_proxy) if _raw_proxy is not None and _raw_proxy.strip() != "" else 1
    except (ValueError, TypeError):
        TRUSTED_PROXY_COUNT = 1
    ADMIN_RATE_LIMIT_LOGIN_MAX = int(os.getenv("ADMIN_RATE_LIMIT_LOGIN_MAX", 5))
    ADMIN_RATE_LIMIT_LOGIN_WINDOW = int(os.getenv("ADMIN_RATE_LIMIT_LOGIN_WINDOW", 900)) # 15 minutes lockout

    # Business Rules & Booking Engine Settings
    # All policies default to server config; owner-confirmed rules are marked
    TIMEZONE_IST = "Asia/Kolkata"
    OPENING_HOUR_IST = 9           # Confirmed: 09:00 AM
    CLOSING_HOUR_IST = 22          # Confirmed: 10:00 PM (22:00)
    BUFFER_MINUTES = 30            # Confirmed: 30 minutes sanitization buffer
    MIN_DURATION_HOURS = 1         # Confirmed: 1 hour minimum
    MAX_DURATION_HOURS = 6         # Confirmed: 6 hours maximum
    MAX_ADVANCE_BOOKING_DAYS = int(os.getenv("MAX_ADVANCE_BOOKING_DAYS", 90))
    SLOT_UNIT_MINUTES = 30         # Anti-double-booking unit granularity
    DEFAULT_ROOM_ID = "main"       # Single room ("main"), extensible
    ALLOW_BUFFER_PAST_CLOSING = True # Unconfirmed: Cleanup buffer 22:00-22:30 allowed

    # Confirmed Owner & Venue Metadata
    WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "917842704429")
    HOST_NAME = "Kiran Kumar"
    VENUE_ADDRESS = "Beside Durga Mart, Vadlamudi, Guntur, Andhra Pradesh 522213"

    # Rate Limiting Settings (Anti-Slot Hoarding)
    RATE_LIMIT_HOLD_PER_IP_MAX = int(os.getenv("RATE_LIMIT_HOLD_PER_IP_MAX", 10))
    RATE_LIMIT_HOLD_PER_IP_WINDOW = int(os.getenv("RATE_LIMIT_HOLD_PER_IP_WINDOW", 60))
    RATE_LIMIT_HOLD_PER_PHONE_MAX = int(os.getenv("RATE_LIMIT_HOLD_PER_PHONE_MAX", 3))
    RATE_LIMIT_HOLD_PER_PHONE_WINDOW = int(os.getenv("RATE_LIMIT_HOLD_PER_PHONE_WINDOW", 600))

    @classmethod
    def validate_production(cls):
        """Fail fast if required variables are missing or insecure in production mode."""
        if cls.FLASK_ENV.lower() == "production" or not cls.DEBUG:
            errors = []
            if not cls.MONGODB_URI or "replace-with" in cls.MONGODB_URI or "<" in cls.MONGODB_URI or ">" in cls.MONGODB_URI:
                errors.append("MONGODB_URI is missing or contains placeholder markers ('<', '>', 'replace-with')")
            if not cls.JWT_SECRET_KEY or cls.JWT_SECRET_KEY == "dev-secret-key-change-in-prod" or "replace-with" in cls.JWT_SECRET_KEY:
                errors.append("JWT_SECRET_KEY is insecure or using default dev secret ('dev-secret-key-change-in-prod')")
            if not cls.FRONTEND_ORIGIN or cls.FRONTEND_ORIGIN == "*":
                errors.append("FRONTEND_ORIGIN cannot be '*' or empty in production")
            if not cls.ADMIN_COOKIE_SECURE:
                errors.append("ADMIN_COOKIE_SECURE must be True in production over HTTPS")

            if errors:
                raise ValueError("CRITICAL: Production configuration validation failed:\n - " + "\n - ".join(errors))
