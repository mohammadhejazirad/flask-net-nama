"""Signed cookie carries only opaque identity/version; CSRF state stays in RAM."""

import secrets
import time

from flask.sessions import SecureCookieSessionInterface


class MemoryCSRFSessionInterface(SecureCookieSessionInterface):
    def open_session(self, app, request):
        session = super().open_session(app, request)
        if session is None:
            return None
        store = app.extensions["sessions"]
        with store.lock:
            now = time.monotonic()
            store.csrf = {sid: value for sid, value in store.csrf.items() if value[1] > now}
            entry = store.csrf.get(session.get("sid"))
            if entry:
                session["csrf_token"] = entry[0]
        return session

    def save_session(self, app, session, response):
        name = self.get_cookie_name(app)
        if not session:
            response.delete_cookie(
                name,
                domain=self.get_cookie_domain(app),
                path=self.get_cookie_path(app),
                secure=self.get_cookie_secure(app),
                httponly=True,
                samesite="Lax",
            )
            return
        if not self.should_set_cookie(app, session):
            return
        sid = session.get("sid") or secrets.token_urlsafe(32)
        session["sid"] = sid
        store = app.extensions["sessions"]
        with store.lock:
            if session.get("csrf_token"):
                if len(store.csrf) >= 1024:
                    store.csrf.pop(next(iter(store.csrf)))
                store.csrf[sid] = (session["csrf_token"], time.monotonic() + store.ttl)
        value = self.get_signing_serializer(app).dumps(
            {"sid": sid, "auth_version": session.get("auth_version", 0)}
        )
        response.set_cookie(
            name,
            value,
            max_age=store.ttl,
            httponly=True,
            secure=self.get_cookie_secure(app),
            samesite="Lax",
            path=self.get_cookie_path(app),
            domain=self.get_cookie_domain(app),
        )
        response.vary.add("Cookie")
