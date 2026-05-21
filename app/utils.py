import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import abort, request, session, redirect, url_for
from flask.sessions import SecureCookieSessionInterface


CSRF_EXEMPT_ENDPOINTS = {
    "ai.chat",
    "auth.session_login",
    "chat.typing_status",
    "social.api_block_toggle",
}


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapper


def init_session_interface(app):
    app.session_interface = SecureCookieSessionInterface()


def get_csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def should_enforce_csrf():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    if request.endpoint in CSRF_EXEMPT_ENDPOINTS:
        return False
    return not request.is_json


def validate_csrf():
    token = (
        request.form.get("_csrf_token")
        or request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
    )
    if not token or token != session.get("_csrf_token"):
        abort(400)


def normalize_text(value, max_length=255):
    return (value or "").strip()[:max_length]


def parse_interests(value, max_items=20, item_length=60):
    interests = []
    seen = set()
    for part in (value or "").split(","):
        cleaned = normalize_text(part, item_length)
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        interests.append(cleaned)
        seen.add(key)
        if len(interests) >= max_items:
            break
    return interests


def is_safe_photo_url(value):
    candidate = normalize_text(value, 500)
    if not candidate:
        return True

    parsed = urlparse(candidate)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
