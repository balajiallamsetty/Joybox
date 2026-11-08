import re
from marshmallow import Schema, fields, validate, validates_schema, ValidationError, EXCLUDE

def validate_password_policy(password: str):
    if len(password) < 10:
        raise ValidationError("Password must be at least 10 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        raise ValidationError("Password must contain at least one numeric digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValidationError("Password must contain at least one special character.")

class AdminLoginSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    username = fields.String(required=True, validate=validate.Length(min=3, max=50))
    password = fields.String(required=True, validate=validate.Length(min=6, max=128))

class AdminChangePasswordSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    oldPassword = fields.String(required=False, validate=validate.Length(min=6, max=128))
    currentPassword = fields.String(required=False, validate=validate.Length(min=6, max=128))
    newPassword = fields.String(required=True, validate=validate_password_policy)

    @validates_schema
    def validate_current_password(self, data, **kwargs):
        if not data.get("oldPassword") and not data.get("currentPassword"):
            raise ValidationError("Current password is required.", field_name="oldPassword")

class AdminUpdateBookingSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    bookingStatus = fields.String(load_default=None, validate=validate.OneOf([
        "hold_placed", "confirmed", "cancelled", "completed", "cancelled_due_to_conflict"
    ]))
    paymentStatus = fields.String(load_default=None, validate=validate.OneOf([
        "unpaid", "paid", "refunded", "partially_refunded"
    ]))
    notes = fields.String(load_default=None, validate=validate.Length(max=1000))
    operationalNotes = fields.String(load_default=None, validate=validate.Length(max=1000))
    celebrantName = fields.String(load_default=None, validate=validate.Length(max=100))
    celebrantAge = fields.Integer(load_default=None, validate=validate.Range(min=1, max=120))
    occasionType = fields.String(load_default=None, validate=validate.Length(max=50))
    cancellationReason = fields.String(load_default=None, validate=validate.Length(max=500))

class AdminCreateBookingSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    packageCode = fields.String(required=True, validate=validate.Length(min=2, max=30))
    addOnCodes = fields.List(fields.String(), load_default=[])
    date = fields.String(required=True, validate=validate.Regexp(r"^\d{4}-\d{2}-\d{2}$"))
    startTime = fields.String(required=True, validate=validate.Regexp(r"^\d{2}:\d{2}$"))
    durationHours = fields.Integer(required=True, validate=validate.Range(min=1, max=6))
    customerName = fields.String(required=True, validate=validate.Length(min=2, max=100))
    customerPhone = fields.String(required=True, validate=validate.Length(min=10, max=15))
    customerEmail = fields.Email(load_default="")
    celebrantName = fields.String(load_default="", validate=validate.Length(max=100))
    celebrantAge = fields.Integer(load_default=None, validate=validate.Range(min=1, max=120))
    occasionType = fields.String(load_default="birthday", validate=validate.Length(max=50))
    notes = fields.String(required=True, validate=validate.Length(min=3, max=1000))
    roomId = fields.String(load_default="main")
    paymentMethod = fields.String(load_default="offline", validate=validate.OneOf(["offline", "cash", "upi_manual", "card_manual"]))

class AdminCreatePackageSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    code = fields.String(required=True, validate=validate.Regexp(r"^[a-z0-9_]+$"))
    name = fields.String(required=True, validate=validate.Length(min=3, max=100))
    pricePerHourMinor = fields.Integer(required=True, validate=validate.Range(min=100))
    currency = fields.String(load_default="INR")
    features = fields.List(fields.String(), load_default=[])
    description = fields.String(load_default="", validate=validate.Length(max=1000))
    displayOrder = fields.Integer(load_default=1)
    isActive = fields.Boolean(load_default=True)

class AdminUpdatePackageSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(load_default=None, validate=validate.Length(min=3, max=100))
    pricePerHourMinor = fields.Integer(load_default=None, validate=validate.Range(min=100))
    features = fields.List(fields.String(), load_default=None)
    description = fields.String(load_default=None, validate=validate.Length(max=1000))
    displayOrder = fields.Integer(load_default=None)
    isActive = fields.Boolean(load_default=None)

class AdminCreateAddOnSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    code = fields.String(required=True, validate=validate.Regexp(r"^[a-z0-9_]+$"))
    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    priceMinor = fields.Integer(required=True, validate=validate.Range(min=0))
    currency = fields.String(load_default="INR")
    category = fields.String(load_default="General")
    description = fields.String(load_default="", validate=validate.Length(max=500))
    isIncludedInPackage = fields.Boolean(load_default=False)
    displayOrder = fields.Integer(load_default=1)
    isActive = fields.Boolean(load_default=True)

class AdminUpdateAddOnSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(load_default=None, validate=validate.Length(min=2, max=100))
    priceMinor = fields.Integer(load_default=None, validate=validate.Range(min=0))
    category = fields.String(load_default=None)
    description = fields.String(load_default=None, validate=validate.Length(max=500))
    isIncludedInPackage = fields.Boolean(load_default=None)
    displayOrder = fields.Integer(load_default=None)
    isActive = fields.Boolean(load_default=None)

class AdminCreateAvailabilityBlockSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    roomId = fields.String(load_default="main")
    date = fields.String(required=True, validate=validate.Regexp(r"^\d{4}-\d{2}-\d{2}$"))
    startTime = fields.String(required=True, validate=validate.Regexp(r"^\d{2}:\d{2}$"))
    durationHours = fields.Integer(required=True, validate=validate.Range(min=1, max=14))
    reason = fields.String(required=True, validate=validate.Length(min=3, max=500))

class AdminUpdateInquirySchema(Schema):
    class Meta:
        unknown = EXCLUDE

    status = fields.String(required=True, validate=validate.OneOf(["new", "contacted", "converted", "closed"]))
    adminNotes = fields.String(load_default="", validate=validate.Length(max=1000))

