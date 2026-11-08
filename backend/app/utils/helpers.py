from datetime import datetime, timezone
from bson import ObjectId

def utcnow():
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)

def serialize_doc(doc):
    """Recursively convert Mongo ObjectId and datetimes to JSON-serializable types."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        result = {}
        for k, v in doc.items():
            if k == "_id" and isinstance(v, ObjectId):
                result["id"] = str(v)
            elif isinstance(v, ObjectId):
                result[k] = str(v)
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                result[k] = serialize_doc(v)
            else:
                result[k] = v
        return result
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.isoformat()
    return doc

def mask_phone(phone_str):
    """Mask phone for customer privacy, keeping only last 4 digits."""
    if not phone_str:
        return ""
    digits = "".join([c for c in str(phone_str) if c.isdigit()])
    if len(digits) >= 4:
        return f"****{digits[-4:]}"
    return "****"

def format_customer_display_name(full_name: str) -> str:
    """Formats customer full name into public-safe initial representation (e.g. 'Ravi K.')."""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."

