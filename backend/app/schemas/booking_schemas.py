from marshmallow import Schema, fields, validate, validates, ValidationError, EXCLUDE, RAISE
import re

class InquirySchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    phone = fields.String(required=True, validate=validate.Length(min=8, max=20))
    preferredDate = fields.String(load_default="", validate=validate.Length(max=30))
    preferredTime = fields.String(load_default="", validate=validate.Length(max=30))
    packageCode = fields.String(load_default="basic", validate=validate.OneOf(["basic", "gold", "diamond"]))
    durationHours = fields.Integer(load_default=1, validate=validate.Range(min=1, max=6))
    message = fields.String(load_default="", validate=validate.Length(max=2000))
    language = fields.String(load_default="en", validate=validate.OneOf(["en", "te"]))

class QuoteRequestSchema(Schema):
    class Meta:
        unknown = RAISE

    packageCode = fields.String(required=True, validate=validate.OneOf(["basic", "gold", "diamond"]))
    durationHours = fields.Integer(required=True, strict=True, validate=validate.Range(min=1, max=6))
    addOnCodes = fields.List(fields.String(), load_default=[])
    applyPromo = fields.Boolean(load_default=True)
    date = fields.String(load_default=None)
    customerPhone = fields.String(load_default=None)
    gstRatePercent = fields.Float(load_default=None, validate=validate.Range(min=0.0, max=100.0))

class AvailabilityQuerySchema(Schema):
    class Meta:
        unknown = EXCLUDE

    date = fields.String(required=True)
    durationHours = fields.Integer(load_default=1, validate=validate.Range(min=1, max=6))
    roomId = fields.String(load_default="main", validate=validate.Length(min=1, max=50))

    @validates("date")
    def validate_date(self, value, **kwargs):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value.strip()):
            raise ValidationError("Invalid date format. Expected YYYY-MM-DD.")

class BookingHoldRequestSchema(Schema):
    class Meta:
        unknown = RAISE

    packageCode = fields.String(required=True, validate=validate.OneOf(["basic", "gold", "diamond"]))
    durationHours = fields.Integer(required=True, strict=True, validate=validate.Range(min=1, max=6))
    date = fields.String(required=True)
    startTime = fields.String(required=True)
    roomId = fields.String(load_default="main", validate=validate.Length(min=1, max=50))
    addOnCodes = fields.List(fields.String(), load_default=[])
    applyPromo = fields.Boolean(load_default=True)
    gstRatePercent = fields.Float(load_default=None, validate=validate.Range(min=0.0, max=100.0))
    celebrantName = fields.String(load_default="", validate=validate.Length(max=100))
    celebrantAge = fields.Integer(load_default=None, allow_none=True)
    occasionType = fields.String(load_default="birthday", validate=validate.Length(max=50))
    customerName = fields.String(required=True, validate=validate.Length(min=2, max=100))
    customerPhone = fields.String(required=True, validate=validate.Length(min=8, max=20))
    customerEmail = fields.String(load_default="", validate=validate.Length(max=100))
    notes = fields.String(load_default="", validate=validate.Length(max=1000))

    @validates("date")
    def validate_date(self, value, **kwargs):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value.strip()):
            raise ValidationError("Invalid date format. Expected YYYY-MM-DD.")

    @validates("startTime")
    def validate_start_time(self, value, **kwargs):
        if not re.match(r"^\d{1,2}:\d{2}$", value.strip()):
            raise ValidationError("Invalid startTime format. Expected HH:MM.")

class BookingCreateRequestSchema(Schema):
    class Meta:
        unknown = RAISE

    holdId = fields.String(required=True, validate=validate.Length(min=24, max=24))

    @validates("holdId")
    def validate_object_id(self, value, **kwargs):
        if not re.match(r"^[0-9a-fA-F]{24}$", value):
            raise ValidationError("Invalid holdId. Must be a 24-character hexadecimal ObjectId.")

class BookingCancelRequestSchema(Schema):
    class Meta:
        unknown = RAISE

    token = fields.String(load_default="", validate=validate.Length(max=100))
    reason = fields.String(load_default="", validate=validate.Length(max=500))
