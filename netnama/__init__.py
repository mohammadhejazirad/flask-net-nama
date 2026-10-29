import atexit
import json
from datetime import timedelta
from pathlib import Path

from flask import Flask, g, jsonify, request
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError

from netnama._version import __version__
from netnama.config import Settings
from netnama.core.jobs import CapacityError, JobStore
from netnama.core.scheduler import Scheduler
from netnama.core.target_policy import TargetPolicy
from netnama.core.validation import ValidationError
from netnama.resources.manager import ResourceManager


def create_app(test_config=None):
    app = Flask(__name__)
    test_config = test_config or {}
    settings = Settings(test_config.get("DATA_DIR"), test_config.get("TESTING", False))
    app.config.update(
        SECRET_KEY=settings.secret,
        MAX_CONTENT_LENGTH=1150000,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.secure_cookie,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
        WTF_CSRF_TIME_LIMIT=3600,
        SESSION_REFRESH_EACH_REQUEST=False,
    )
    app.config.update(test_config)

    @app.before_request
    def reject_unauthenticated_api():
        if request.path.startswith("/api/") or request.path in ("/auth/logout", "/auth/password"):
            from flask import session

            if not app.extensions["sessions"].valid(session.get("sid"), session.get("auth_version")):
                return jsonify(error="authentication_required"), 401

    CSRFProtect(app)
    from netnama.auth.routes import Sessions, bp as auth
    from netnama.api.routes import StreamLimit, bp as api
    from netnama.web.routes import bp as web

    app.extensions["settings"] = settings
    app.extensions["sessions"] = Sessions()
    from netnama.auth.session import MemoryCSRFSessionInterface

    app.session_interface = MemoryCSRFSessionInterface()
    app.extensions["jobs"] = JobStore(settings.result_ttl, settings.max_ram_mb)
    app.extensions["streams"] = StreamLimit()
    app.extensions["resources"] = ResourceManager(settings.data_dir / "resources")
    app.extensions["scheduler"] = Scheduler(TargetPolicy(settings.allow_private), settings.public)
    atexit.register(app.extensions["scheduler"].close)
    folder = Path(__file__).parent / "locales"
    app.extensions["catalogs"] = {
        lang: json.loads((folder / f"{lang}.json").read_text("utf-8")) for lang in ("fa", "en")
    }
    app.register_blueprint(auth)
    app.register_blueprint(api)
    app.register_blueprint(web)

    @app.before_request
    def locale():
        g.locale = request.args.get("lang", request.headers.get("X-NetNama-Locale", "fa"))
        if g.locale not in ("fa", "en"):
            g.locale = "fa"

    @app.context_processor
    def context():
        catalog = app.extensions["catalogs"][g.locale]
        return {
            "t": lambda key: catalog.get(key, key),
            "catalogs": app.extensions["catalogs"],
            "locale": g.locale,
            "dir": "rtl" if g.locale == "fa" else "ltr",
            "app_version": __version__,
        }

    @app.after_request
    def headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if not request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        if response.status_code == 429 and "Retry-After" not in response.headers:
            response.headers["Retry-After"] = "300" if request.path == "/auth/login" else "15"
        if settings.secure_cookie:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/healthz")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(ValidationError)
    def validation_error(exc):
        return jsonify(error=str(exc)), 422

    @app.errorhandler(ValueError)
    @app.errorhandler(UnicodeError)
    def value_error(exc):
        return jsonify(error="invalid_input"), 422

    @app.errorhandler(CapacityError)
    def capacity_error(exc):
        return jsonify(error="capacity_exceeded"), 429, {"Retry-After": "15"}

    @app.errorhandler(CSRFError)
    def csrf_error(exc):
        return jsonify(error="csrf_error"), 400

    @app.errorhandler(404)
    @app.errorhandler(410)
    @app.errorhandler(413)
    @app.errorhandler(500)
    def http_error(exc):
        return jsonify(
            error={404: "not_found", 410: "expired", 413: "input_too_large", 500: "server_error"}[exc.code]
        ), exc.code

    return app
