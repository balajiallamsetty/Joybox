import logging
from app.utils.logging_utils import scrub_pii, PIIScrubbingFilter

def test_scrub_pii_phone_and_email():
    # Test phone masking
    raw_phone_msg = "Booking hold created for customer with phone 9876543210 and +91 9123456789."
    scrubbed = scrub_pii(raw_phone_msg)
    assert "9876543210" not in scrubbed
    assert "9123456789" not in scrubbed
    assert "****3210" in scrubbed
    assert "****6789" in scrubbed

    # Test email redaction
    raw_email_msg = "Sent notification to priya.k@example.com successfully."
    scrubbed_email = scrub_pii(raw_email_msg)
    assert "priya.k@example.com" not in scrubbed_email
    assert "[REDACTED_EMAIL]" in scrubbed_email

def test_pii_scrubbing_filter_record():
    logger = logging.getLogger("test_pii_logger")
    logger.setLevel(logging.INFO)
    filt = PIIScrubbingFilter()

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Hold requested by phone %s with email %s",
        args=("9988776655", "user@joybox.party"),
        exc_info=None
    )

    filt.filter(record)
    assert "****6655" in record.args[0]
    assert "[REDACTED_EMAIL]" in record.args[1]
