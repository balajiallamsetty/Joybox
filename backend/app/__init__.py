import os
import logging
import uuid
from flask import Flask, request, g, has_request_context, has_app_context
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from .config import Config
from .extensions import init_mongo
from .routes.public_routes import public_bp
from .routes.payment_routes import payment_bp
from .routes.admin_routes import admin_bp
from .repositories import AdminSessionRepository, UserRepository, AuditLogRepository
from .utils import api_error

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # In test environments without explicit override, allow existing booking suites to run
    if app.config.get("TESTING") and "BOOKINGS_OPEN" not in (test_config or {}) and "BOOKINGS_OPEN" not in os.environ:
        app.config["BOOKINGS_OPEN"] = True

    # Fail fast if required configuration is missing in production
    if not app.config.get("TESTING") and (Config.FLASK_ENV.lower() == "production" or not Config.DEBUG):
        Config.validate_production()

    # Configure structured logging
    app_log_level = logging.INFO
    log_level_env = Config.FLASK_ENV.lower()
    if Config.DEBUG or log_level_env == "development":
        app_log_level = logging.INFO  # Keep application at INFO; DEBUG only if explicitly requested

    logging.basicConfig(
        level=app_log_level,
        format="%(asctime)s [%(levelname)s] [req_id=%(request_id)s] %(message)s"
    )

    # BUG-14: Preserve connection diagnostics and slow-query warnings at INFO,
    # while selectively silencing high-frequency heartbeat and topology noise to WARNING
    logging.getLogger("pymongo").setLevel(logging.INFO)
    logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
    logging.getLogger("pymongo.serverSelection").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.INFO if Config.DEBUG else logging.WARNING)

    # Configure ProxyFix for trusted reverse proxy headers (e.g. Render) (BUG-10, S1)
    try:
        raw_val = app.config.get("TRUSTED_PROXY_COUNT")
        trusted_proxy_count = int(raw_val) if raw_val is not None and str(raw_val).strip() != "" else 1
    except (ValueError, TypeError):
        trusted_proxy_count = 1

    if trusted_proxy_count > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=trusted_proxy_count,
            x_proto=trusted_proxy_count,
            x_host=trusted_proxy_count,
            x_prefix=trusted_proxy_count
        )

    # Safe Request ID filter checking request context
    class RequestIdFilter(logging.Filter):
        def filter(self, record):
            if has_request_context() and hasattr(g, "request_id"):
                record.request_id = g.request_id
            else:
                record.request_id = "-"
            return True

    from app.utils.logging_utils import PIIScrubbingFilter
    pii_filter = PIIScrubbingFilter()

    for handler in logging.root.handlers:
        handler.addFilter(RequestIdFilter())
        handler.addFilter(pii_filter)

    for handler in app.logger.handlers:
        handler.addFilter(RequestIdFilter())
        handler.addFilter(pii_filter)

    @app.before_request
    def set_request_id():
        g.request_id = request.headers.get("X-Request-Id", str(uuid.uuid4())[:8])

    @app.before_request
    def reject_untrusted_browser_origin():
        """Allow the Vercel site origin even when the API Host is Render.

        Missing Origin is allowed for webhooks, health checks, and same-origin
        navigation. A present Origin must be one of FRONTEND_ORIGIN values.
        """
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None
        if request.path.startswith("/api/payments/webhook"):
            return None
        origin = (request.headers.get("Origin") or "").strip().rstrip("/")
        if not origin:
            return None
        allowed = {
            item.strip().rstrip("/")
            for item in str(app.config.get("FRONTEND_ORIGIN", "")).split(",")
            if item.strip()
        }
        if origin not in allowed:
            return api_error(
                "ORIGIN_REJECTED",
                "Request origin is not allowed.",
                status_code=403,
            )
        return None

    @app.after_request
    def apply_security_headers(response):
        if has_request_context() and hasattr(g, "request_id"):
            response.headers["X-Request-Id"] = g.request_id

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        if request.path.startswith("/api/admin") or "Authorization" in request.headers:
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        elif request.path.startswith("/api/packages") or request.path.startswith("/api/add-ons") or request.path.startswith("/api/offers/active"):
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Cache-Control"] = "public, max-age=30, must-revalidate"
        else:
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response

    # CORS configuration with credentials support for HttpOnly admin cookies
    # Normalizes comma-separated origins, trimming whitespace and trailing slashes
    origins = [orig.strip().rstrip("/") for orig in str(app.config.get("FRONTEND_ORIGIN", "")).split(",") if orig.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=True)

    # Database initialization
    init_mongo(app)

    db = app.extensions.get("mongo_db")
    if db is not None:
        app.extensions["admin_session_repo"] = AdminSessionRepository(db)
        app.extensions["user_repo"] = UserRepository(db)
        app.extensions["audit_repo"] = AuditLogRepository(db)

    # Register blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(admin_bp)

    # Global error handlers ensuring standard JSON envelope
    @app.errorhandler(404)
    def handle_not_found(err):
        return api_error("NOT_FOUND", "The requested resource was not found", status_code=404)

    @app.errorhandler(405)
    def handle_method_not_allowed(err):
        return api_error("METHOD_NOT_ALLOWED", "Method is not allowed for this endpoint", status_code=405)

    @app.errorhandler(Exception)
    def handle_unhandled_exception(err):
        app.logger.error(f"Unhandled error: {err}", exc_info=True)
        return api_error("INTERNAL_ERROR", "An unexpected error occurred. Please try again later.", status_code=500)

    return app
