import secrets
import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, current_app, g
from bson import ObjectId

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    import werkzeug.security
    HAS_BCRYPT = False

from ..config import Config
from ..utils.datetime_utils import now_utc
from ..utils import api_error

logger = logging.getLogger(__name__)

# Precomputed dummy hash to ensure constant-time response on nonexistent usernames
DUMMY_BCRYPT_HASH = b"$2b$12$e8kPqZ9f2Zz6uVj0e4JzOuE.C1h6O1rJ1Z4y2e8kPqZ9f2Zz6uVj0"

class AuthenticationError(Exception):
    def __init__(self, message="Invalid username or password.", code="INVALID_CREDENTIALS", status_code=401):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

class AccountLockedError(Exception):
    def __init__(self, message="Account temporarily locked due to consecutive failed logins. Please try again in 30 minutes.", code="ACCOUNT_LOCKED", status_code=423):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

class AdminService:
    def __init__(self, user_repo, session_repo, audit_repo, config=None):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.audit_repo = audit_repo
        self.config = config or Config

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        if not plain_password or not hashed_password:
            return False
        if HAS_BCRYPT and hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            try:
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return False
        elif not HAS_BCRYPT and hasattr(werkzeug.security, "check_password_hash"):
            return werkzeug.security.check_password_hash(hashed_password, plain_password)
        elif ":" in hashed_password:
            # PBKDF2 fallback
            try:
                salt_hex, dk_hex = hashed_password.split(":")
                salt = bytes.fromhex(salt_hex)
                computed = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000).hex()
                return hmac.compare_digest(computed, dk_hex)
            except Exception:
                return False
        return False

    @staticmethod
    def hash_password(plain_password: str) -> str:
        if HAS_BCRYPT:
            salt = bcrypt.gensalt(rounds=12)
            return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")
        else:
            return werkzeug.security.generate_password_hash(plain_password, method="scrypt")

    def login(self, username: str, password: str, client_ip: str = None, user_agent: str = None) -> dict:
        now_u = now_utc()
        username_clean = (username or "").strip().lower()

        user = self.user_repo.find_by_username(username_clean) if username_clean else None

        if not user:
            # Constant-time dummy verification to mitigate timing-based user enumeration
            if HAS_BCRYPT:
                bcrypt.checkpw(password.encode("utf-8"), DUMMY_BCRYPT_HASH)
            raise AuthenticationError("Invalid username or password.")

        if not user.get("isActive", True):
            raise AuthenticationError("Account is inactive. Please contact the administrator.")

        # Account lockout check
        lockout_until = user.get("lockoutUntil")
        if lockout_until and lockout_until > now_u:
            remaining_mins = int((lockout_until - now_u).total_seconds() / 60.0) + 1
            raise AccountLockedError(f"Account temporarily locked. Please try again in {remaining_mins} minutes.")

        # Password verification
        if not self.verify_password(password, user.get("passwordHash", "")):
            failed_attempts = user.get("failedLoginAttempts", 0) + 1
            max_attempts = getattr(self.config, "ADMIN_MAX_FAILED_LOGINS", 5)
            lockout_mins = getattr(self.config, "ADMIN_LOCKOUT_MINUTES", 30)

            extra_fields = {"failedLoginAttempts": failed_attempts, "updatedAt": now_u}
            if failed_attempts >= max_attempts:
                extra_fields["lockoutUntil"] = now_u + timedelta(minutes=lockout_mins)

            self.user_repo.update_user(user["_id"], extra_fields)

            self.write_audit_log(
                actor_id=user["_id"],
                actor_username=user["username"],
                actor_role=user.get("role", "staff"),
                action="ADMIN_LOGIN_FAILED",
                target_collection="users",
                target_id=str(user["_id"]),
                details={"reason": "Invalid password", "failedAttempts": failed_attempts},
                ip_address=client_ip
            )
            raise AuthenticationError("Invalid username or password.")

        # Successful authentication: reset failed attempts
        self.user_repo.update_user(
            user["_id"],
            {"failedLoginAttempts": 0, "lockoutUntil": None, "lastLoginAt": now_u, "updatedAt": now_u}
        )

        # Issue 256-bit unguessable session token and CSRF token
        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()

        session_lifetime = timedelta(hours=getattr(self.config, "ADMIN_SESSION_LIFETIME_HOURS", 8))
        idle_timeout = timedelta(minutes=getattr(self.config, "ADMIN_SESSION_IDLE_MINUTES", 30))

        session_doc = {
            "_id": ObjectId(),
            "userId": user["_id"],
            "username": user["username"],
            "role": user.get("role", "staff"),
            "tokenHash": token_hash,
            "csrfToken": csrf_token,
            "createdAt": now_u,
            "lastAccessedAt": now_u,
            "expiresAt": now_u + session_lifetime,
            "idleExpiresAt": now_u + idle_timeout,
            "ipAddress": client_ip,
            "userAgent": user_agent,
            "isRevoked": False,
            "revokedAt": None
        }
        self.session_repo.create_session(session_doc)

        self.write_audit_log(
            actor_id=user["_id"],
            actor_username=user["username"],
            actor_role=user.get("role", "staff"),
            action="ADMIN_LOGIN_SUCCESS",
            target_collection="adminSessions",
            target_id=str(session_doc["_id"]),
            details={"ip": client_ip, "userAgent": user_agent},
            ip_address=client_ip
        )

        return {
            "sessionToken": session_token,
            "csrfToken": csrf_token,
            "user": {
                "id": str(user["_id"]),
                "username": user["username"],
                "displayName": user.get("displayName", user["username"].title()),
                "role": user.get("role", "staff"),
                "email": user.get("email", "")
            }
        }

    def logout(self, session_doc: dict, client_ip: str = None):
        if not session_doc:
            return
        now_u = now_utc()
        self.session_repo.revoke_session(session_doc.get("tokenHash"), now_u)
        self.write_audit_log(
            actor_id=session_doc.get("userId"),
            actor_username=session_doc.get("username", "admin"),
            actor_role=session_doc.get("role", "staff"),
            action="ADMIN_LOGOUT",
            target_collection="adminSessions",
            target_id=str(session_doc.get("_id", "")),
            details={"ip": client_ip},
            ip_address=client_ip
        )

    def change_password(self, user_id, old_password: str, new_password: str, client_ip: str = None):
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found.")

        if not self.verify_password(old_password, user.get("passwordHash", "")):
            raise AuthenticationError("Current password is incorrect.", code="INVALID_OLD_PASSWORD")

        new_hash = self.hash_password(new_password)
        now_u = now_utc()

        self.user_repo.update_password(user["_id"], new_hash, now_u)
        # Revoke all existing sessions for this user so old sessions cannot be used
        if hasattr(self.session_repo, "revoke_all_user_sessions"):
            self.session_repo.revoke_all_user_sessions(user["_id"], now_u)
        elif hasattr(self.session_repo, "revoke_all_for_user"):
            self.session_repo.revoke_all_for_user(user["_id"], now_u)

        self.write_audit_log(
            actor_id=user["_id"],
            actor_username=user["username"],
            actor_role=user.get("role", "staff"),
            action="PASSWORD_CHANGE",
            target_collection="users",
            target_id=str(user["_id"]),
            details={"message": "Password changed successfully; all active sessions revoked."},
            ip_address=client_ip
        )

    def write_audit_log(
        self,
        actor_id,
        actor_username: str,
        actor_role: str,
        action: str,
        target_collection: str,
        target_id: str,
        details: dict = None,
        request_id: str = None,
        ip_address: str = None
    ):
        if not self.audit_repo:
            return
        log_doc = {
            "_id": ObjectId(),
            "actorId": actor_id if isinstance(actor_id, ObjectId) else ObjectId(actor_id) if actor_id else None,
            "actorUsername": actor_username or "system",
            "actorRole": actor_role or "unknown",
            "action": action,
            "targetCollection": target_collection,
            "targetId": str(target_id) if target_id else None,
            "details": details or {},
            "requestId": request_id,
            "ipAddress": ip_address,
            "createdAt": now_utc()
        }
        try:
            self.audit_repo.insert(log_doc)
        except Exception as e:
            logger.error(f"Failed to record audit log: {str(e)}")
            # For financial and blocking operations, re-raise to fail closed
            if action in ("REFUND_PROCESS", "AVAILABILITY_BLOCK_CREATE", "OFFLINE_BOOKING_CREATE"):
                raise


def require_admin_session(f):
    """
    Decorator that authenticates administrator sessions via HttpOnly cookie or Authorization header.
    Validates token hash, absolute expiration, and idle timeout. Touches session on active access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        cookie_name = current_app.config.get(
            "ADMIN_SESSION_COOKIE_NAME",
            current_app.config.get("ADMIN_COOKIE_NAME", "joybox_admin_session")
        )
        token = request.cookies.get(cookie_name)

        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()

        if not token or not token.strip():
            return api_error("UNAUTHORIZED", "Authentication required. Please log in.", status_code=401)

        token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
        session_repo = current_app.extensions.get("admin_session_repo")
        user_repo = current_app.extensions.get("user_repo")

        if not session_repo:
            return api_error("INTERNAL_ERROR", "Session service unavailable.", status_code=500)

        session = session_repo.find_by_token_hash(token_hash)
        now_u = now_utc()

        if not session or session.get("revokedAt") is not None:
            return api_error("UNAUTHORIZED", "Session expired or revoked. Please log in again.", status_code=401)

        # Check absolute expiration
        if session["expiresAt"] <= now_u:
            session_repo.revoke_session(token_hash, now_u)
            return api_error("UNAUTHORIZED", "Session expired. Please log in again.", status_code=401)

        # Check idle expiration
        idle_exp = session.get("idleExpiresAt")
        if idle_exp and idle_exp <= now_u:
            session_repo.revoke_session(token_hash, now_u)
            return api_error("UNAUTHORIZED", "Session timed out due to inactivity.", status_code=401)

        # Touch session idle timeout
        idle_mins = getattr(current_app.config, "ADMIN_SESSION_IDLE_MINUTES", 30)
        session_repo.touch_session(token_hash, idle_mins, now_u)

        # Load user
        user = user_repo.find_by_id(session["userId"]) if user_repo else None
        if not user or not user.get("isActive", True):
            session_repo.revoke_session(token_hash, now_u)
            return api_error("UNAUTHORIZED", "Account is inactive or disabled.", status_code=401)

        g.admin_session = session
        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function


def require_role(*allowed_roles):
    """
    Decorator that enforces role-based authorization for the authenticated administrator.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user:
                return api_error("UNAUTHORIZED", "Authentication required.", status_code=401)

            role = user.get("role", "staff")
            if role not in allowed_roles:
                return api_error(
                    "FORBIDDEN",
                    f"Access denied. Role '{role}' does not have permission for this resource.",
                    status_code=403
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_csrf(f):
    """
    Decorator that enforces custom header CSRF token check on mutating HTTP requests.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ("POST", "PATCH", "PUT", "DELETE"):
            header_name = getattr(current_app.config, "CSRF_HEADER_NAME", "X-CSRF-Token")
            submitted_token = request.headers.get(header_name)
            session = getattr(g, "admin_session", None)

            if not session or not submitted_token:
                return api_error("CSRF_TOKEN_MISSING", "X-CSRF-Token header is required for state-changing operations.", status_code=403)

            expected_token = session.get("csrfToken", "")
            if not hmac.compare_digest(submitted_token.strip(), expected_token):
                return api_error("CSRF_TOKEN_INVALID", "Invalid CSRF token.", status_code=403)

        return f(*args, **kwargs)
    return decorated_function

