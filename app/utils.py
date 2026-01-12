from functools import wraps
from flask import session, redirect, url_for
from flask.sessions import SecureCookieSessionInterface

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapper

def init_session_interface(app):
    app.session_interface = SecureCookieSessionInterface()
