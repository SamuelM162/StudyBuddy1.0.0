from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from app.firebase_app import db
from firebase_admin import auth as firebase_auth

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

def _firebase_web_config():
    """Return Firebase Web SDK config dict for client-side initialization."""
    return current_app.config.get("FIREBASE_CONFIG", {})

@auth_bp.route("/signup", methods=["GET"])
def signup():
    # Signup is handled on the client via Firebase Web SDK (password never reaches the server).
    # After signup, the client sends an ID token to /auth/sessionLogin.
    return render_template("auth_signup.html", firebase_config=_firebase_web_config())


@auth_bp.route("/login", methods=["GET"])
def login():
    # Login is handled on the client via Firebase Web SDK (password never reaches the server).
    # After login, the client sends an ID token to /auth/sessionLogin.
    return render_template("auth_login.html", firebase_config=_firebase_web_config())


@auth_bp.route("/sessionLogin", methods=["POST"])
def session_login():
    """
    Client authenticates with Firebase Web SDK (email/password, Google, Microsoft, etc.),
    then posts { idToken } here. Backend verifies token and creates a Flask session.
    """
    payload = request.get_json(silent=True) or {}
    id_token = payload.get("idToken") or payload.get("id_token")

    if not id_token:
        return jsonify({"ok": False, "error": "Missing idToken"}), 400

    try:
        decoded = firebase_auth.verify_id_token(id_token)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Invalid token: {e}"}), 401

    uid = decoded.get("uid")
    email = decoded.get("email") or ""

    if not uid:
        return jsonify({"ok": False, "error": "Token missing uid"}), 401

    session["user_id"] = uid
    session["email"] = email

    # Ensure user profile exists in RTDB (no passwords stored)
    user_ref = db.child("users").child(uid)
    existing = user_ref.get().val()
    if not existing:
        display_name = decoded.get("name") or email or "Student"
        user_ref.set({
            "email": email,
            "display_name": display_name,
            "faculty": "",
            "bio": "",
            "interests": [],
            "is_tutor": False
        })

    return jsonify({"ok": True, "uid": uid, "email": email})


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("main.index"))
