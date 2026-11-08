from marshmallow import Schema, fields, validate, RAISE

class CreatePaymentOrderSchema(Schema):
    class Meta:
        unknown = RAISE

    bookingReference = fields.String(required=True, validate=validate.Length(min=5, max=30))
    token = fields.String(required=True, validate=validate.Length(min=10, max=256))
    idempotencyKey = fields.String(load_default=None, validate=validate.Length(max=100))

class VerifyPaymentSchema(Schema):
    class Meta:
        unknown = RAISE

    bookingReference = fields.String(required=True, validate=validate.Length(min=5, max=30))
    token = fields.String(required=True, validate=validate.Length(min=10, max=256))
    razorpay_order_id = fields.String(required=True, validate=validate.Length(min=5, max=100))
    razorpay_payment_id = fields.String(required=True, validate=validate.Length(min=5, max=100))
    razorpay_signature = fields.String(required=True, validate=validate.Length(min=10, max=256))

class RefundRequestSchema(Schema):
    class Meta:
        unknown = RAISE

    bookingReference = fields.String(required=True, validate=validate.Length(min=5, max=30))
    token = fields.String(required=True, validate=validate.Length(min=10, max=256))
    reason = fields.String(load_default="", validate=validate.Length(max=500))
    amountMinor = fields.Integer(load_default=None, validate=validate.Range(min=100))
    idempotencyKey = fields.String(load_default=None, validate=validate.Length(max=100))
