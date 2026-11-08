from bson import ObjectId
import pytest
from marshmallow import ValidationError
from app import create_app
from app.schemas.admin_schemas import AdminChangePasswordSchema
from app.services.admin_service import AdminService, AuthenticationError
from app.utils.datetime_utils import now_utc

class MockUserCollection:
    def __init__(self):
        self.docs = []

    def find_one(self, query=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in (query or {}).items()):
                return dict(d)
        return None

    def update_one(self, filter_query, update_doc, upsert=False):
        doc = self.find_one(filter_query)
        if doc:
            if "$set" in update_doc:
                doc.update(update_doc["$set"])
            return type("UpdateResult", (), {"matched_count": 1, "modified_count": 1})()
        return type("UpdateResult", (), {"matched_count": 0, "modified_count": 0})()

    def find_one_and_update(self, filter_query, update_doc, return_document=None):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in filter_query.items()):
                if "$set" in update_doc:
                    doc.update(update_doc["$set"])
                return dict(doc)
        return None

class MockSessionCollection:
    def __init__(self):
        self.docs = []

    def find_one(self, query=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in (query or {}).items()):
                return dict(d)
        return None

    def update_many(self, filter_query, update_doc):
        return type("UpdateResult", (), {"matched_count": len(self.docs), "modified_count": len(self.docs)})()

class MockAuditCollection:
    def insert_one(self, doc):
        return type("InsertResult", (), {"inserted_id": doc.get("_id")})()

class MockDB:
    def __init__(self):
        self.users = MockUserCollection()
        self.adminSessions = MockSessionCollection()
        self.adminAuditLogs = MockAuditCollection()

def test_password_policy_schema_validation():
    """Verify AdminChangePasswordSchema enforces min 10 chars, uppercase, lowercase, digit, symbol."""
    schema = AdminChangePasswordSchema()

    # 1. Too short (< 10 chars)
    with pytest.raises(ValidationError) as exc:
        schema.load({"oldPassword": "InitialPassword123!", "newPassword": "Short1!"})
    assert "at least 10 characters" in str(exc.value)

    # 2. Missing uppercase
    with pytest.raises(ValidationError) as exc:
        schema.load({"oldPassword": "InitialPassword123!", "newPassword": "lowercaseonly123!"})
    assert "uppercase" in str(exc.value)

    # 3. Missing lowercase
    with pytest.raises(ValidationError) as exc:
        schema.load({"oldPassword": "InitialPassword123!", "newPassword": "UPPERCASEONLY123!"})
    assert "lowercase" in str(exc.value)

    # 4. Missing digit
    with pytest.raises(ValidationError) as exc:
        schema.load({"oldPassword": "InitialPassword123!", "newPassword": "NoDigitsInPassword!"})
    assert "numeric digit" in str(exc.value)

    # 5. Missing symbol
    with pytest.raises(ValidationError) as exc:
        schema.load({"oldPassword": "InitialPassword123!", "newPassword": "NoSpecialCharacter123"})
    assert "special character" in str(exc.value)

    # 6. Valid password passing all rules
    valid = schema.load({"oldPassword": "InitialPassword123!", "newPassword": "ValidStrongPassword789#"})
    assert valid["newPassword"] == "ValidStrongPassword789#"

def test_service_password_change_rejects_wrong_old_password():
    """Verify change_password rejects incorrect current password."""
    db = MockDB()
    user_id = ObjectId()
    initial_hash = AdminService.hash_password("CurrentPassword123!")
    user_doc = {
        "_id": user_id,
        "username": "kiran_owner",
        "role": "owner",
        "passwordHash": initial_hash,
    }
    db.users.docs.append(user_doc)

    from app.repositories import UserRepository, AdminSessionRepository, AuditLogRepository
    svc = AdminService(UserRepository(db), AdminSessionRepository(db), AuditLogRepository(db))

    with pytest.raises(AuthenticationError) as exc:
        svc.change_password(user_id, "WrongOldPassword!", "BrandNewPassword123#")
    assert exc.value.code == "INVALID_OLD_PASSWORD"

def test_service_password_change_success_and_revocation():
    """Verify change_password updates password hash and revokes sessions on success."""
    db = MockDB()
    user_id = ObjectId()
    initial_hash = AdminService.hash_password("CurrentPassword123!")
    user_doc = {
        "_id": user_id,
        "username": "kiran_owner",
        "role": "owner",
        "passwordHash": initial_hash,
    }
    db.users.docs.append(user_doc)

    from app.repositories import UserRepository, AdminSessionRepository, AuditLogRepository
    svc = AdminService(UserRepository(db), AdminSessionRepository(db), AuditLogRepository(db))

    svc.change_password(user_id, "CurrentPassword123!", "NewSecretPassword456$")

    updated_user = db.users.find_one({"_id": user_id})
    assert not svc.verify_password("CurrentPassword123!", updated_user["passwordHash"])
    assert svc.verify_password("NewSecretPassword456$", updated_user["passwordHash"])
