class BookingException(Exception):
    def __init__(self, message: str, code: str = "BOOKING_ERROR", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

class SlotUnavailableError(BookingException):
    def __init__(self, message: str = "The requested time slot is no longer available. Please select another time."):
        super().__init__(message, code="SLOT_CONFLICT", status_code=409)

class HoldExpiredError(BookingException):
    def __init__(self, message: str = "Booking hold has expired. Please select your time slot again."):
        super().__init__(message, code="HOLD_EXPIRED", status_code=410)

class PromoExhaustedError(BookingException):
    def __init__(self, message: str = "The promotional offer quota has been exhausted."):
        super().__init__(message, code="PROMO_EXHAUSTED", status_code=409)

class IdempotencyConflictError(BookingException):
    def __init__(self, message: str = "Idempotency key collision or conflicting payload."):
        super().__init__(message, code="IDEMPOTENCY_CONFLICT", status_code=409)

class ResourceNotFoundError(BookingException):
    def __init__(self, message: str = "Resource not found."):
        super().__init__(message, code="NOT_FOUND", status_code=404)

class InvalidBookingStateError(BookingException):
    def __init__(self, message: str = "Operation not allowed in current booking state."):
        super().__init__(message, code="INVALID_STATE", status_code=409)

class RateLimitExceededError(BookingException):
    def __init__(self, message: str = "Rate limit exceeded. Please wait before creating more reservation requests."):
        super().__init__(message, code="RATE_LIMITED", status_code=429)

class IdempotencyPayloadMismatchError(BookingException):
    def __init__(self, message: str = "Idempotency key reused with different request payload."):
        super().__init__(message, code="IDEMPOTENCY_PAYLOAD_MISMATCH", status_code=422)

class PaymentVerificationError(BookingException):
    def __init__(self, message: str = "Payment signature verification failed."):
        super().__init__(message, code="PAYMENT_VERIFICATION_FAILED", status_code=400)

class PaymentGatewayError(BookingException):
    def __init__(self, message: str = "Payment gateway error. Please try again."):
        super().__init__(message, code="PAYMENT_GATEWAY_ERROR", status_code=502)

class InvalidPaymentStateError(BookingException):
    def __init__(self, message: str = "Payment operation not allowed in current state."):
        super().__init__(message, code="INVALID_PAYMENT_STATE", status_code=409)

class RefundNotAllowedError(BookingException):
    def __init__(self, message: str = "Refund request not allowed by policy."):
        super().__init__(message, code="REFUND_NOT_ALLOWED", status_code=400)

class LatePaymentSlotTakenError(BookingException):
    def __init__(self, message: str = "Celebration slot was taken before payment completion. Full refund initiated."):
        super().__init__(message, code="LATE_PAYMENT_SLOT_TAKEN", status_code=409)


