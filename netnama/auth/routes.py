import secrets
import threading
import time
from collections import OrderedDict
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

bp = Blueprint("auth", __name__)


class Sessions:
    def __init__(self):
        self.lock = threading.RLock()
        self.active = {}
        self.csrf = {}
        self.attempts = OrderedDict()
        self.ttl = 3600

    def valid(self, sid, version):
        with self.lock:
            now = time.monotonic()
            self.active = {key: expiry for key, expiry in self.active.items() if expiry > now}
            return sid in self.active and version == current_app.extensions["settings"].values["auth_version"]

    def limited(self, key):
        with self.lock:
            now = time.monotonic()
            values = [t for t in self.attempts.pop(key, []) if t > now - 300]
            self.attempts[key] = values
            while len(self.attempts) > 4096:
                self.attempts.popitem(last=False)
            if len(values) >= 8:
                return True
            values.append(now)
            return False


def authenticated(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        store = current_app.extensions["sessions"]
        if not store.valid(session.get("sid"), session.get("auth_version")):
            session.clear()
            if request.path.startswith("/api/") or request.is_json:
                return jsonify(error="authentication_required"), 401
            return redirect(url_for("auth.login"))
        g.owner = session["sid"]
        return fn(*args, **kwargs)

    return wrapper


@bp.route("/auth/login", methods=["GET", "POST"])
def login():
    error = None
    code = 200
    if request.method == "POST":
        store = current_app.extensions["sessions"]
        settings = current_app.extensions["settings"]
        data = request.get_json(silent=True) or request.form
        if store.limited(request.remote_addr):
            error, code = "login_limited", 429
        else:
            valid_password = check_password_hash(
                settings.values["password_hash"], str(data.get("password", ""))
            )
            if data.get("username") == settings.username and valid_password:
                session.clear()
                sid = secrets.token_urlsafe(32)
                session["sid"] = sid
                session["auth_version"] = settings.values["auth_version"]
                session.permanent = True
                with store.lock:
                    if len(store.active) >= 256:
                        store.active.pop(next(iter(store.active)))
                    store.active[sid] = time.monotonic() + store.ttl
                if request.is_json:
                    return jsonify(ok=True)
                return redirect(url_for("web.page"))
            error, code = "login_error", 401
        if request.is_json:
            return jsonify(error=error), code
    return render_template("login.html", error=error), code


@bp.post("/auth/logout")
@authenticated
def logout():
    with current_app.extensions["sessions"].lock:
        current_app.extensions["sessions"].active.pop(session.get("sid"), None)
    session.clear()
    if request.is_json:
        return jsonify(ok=True)
    return redirect(url_for("auth.login"))


@bp.post("/auth/password")
@authenticated
def password():
    data = request.get_json(silent=True) or request.form
    settings = current_app.extensions["settings"]
    if not check_password_hash(settings.values["password_hash"], str(data.get("current_password", ""))):
        return jsonify(error="login_error"), 422
    new = str(data.get("new_password", ""))
    if len(new) < 12 or len(new) > 256:
        return jsonify(error="password_length"), 422
    settings.change_password(new)
    with current_app.extensions["sessions"].lock:
        current_app.extensions["sessions"].active.clear()
    session.clear()
    return jsonify(ok=True)
