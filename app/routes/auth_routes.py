from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from app.firebase_app import db
from app.i18n import tr
from app.universities import is_valid_university
from app.utils import is_safe_photo_url, normalize_text
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
    provided_name = normalize_text(payload.get("display_name") or payload.get("displayName"), 80)
    provided_university = normalize_text(payload.get("university"), 120)
    provided_photo_url = normalize_text(payload.get("photo_url") or payload.get("photoURL"), 500)

    if not id_token:
        return jsonify({"ok": False, "error": "Missing idToken"}), 400
    if provided_university and not is_valid_university(provided_university):
        return jsonify({"ok": False, "error": "Invalid university"}), 400
    if provided_photo_url and not is_safe_photo_url(provided_photo_url):
        return jsonify({"ok": False, "error": "Invalid photo URL"}), 400

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
    token_display_name = normalize_text(decoded.get("name"), 80)
    token_photo_url = normalize_text(decoded.get("picture"), 500)
    display_name = provided_name or token_display_name or normalize_text(email, 80) or "Student"
    photo_url = provided_photo_url or token_photo_url

    if not existing:
        user_ref.set({
            "email": email,
            "display_name": display_name,
            "faculty": "",
            "university": provided_university,
            "bio": "",
            "interests": [],
            "photo_url": photo_url if is_safe_photo_url(photo_url) else "",
            "is_tutor": False,
        })
    else:
        updates = {}
        if email and not existing.get("email"):
            updates["email"] = email
        if provided_name and existing.get("display_name") != provided_name:
            updates["display_name"] = provided_name
        if provided_university and existing.get("university") != provided_university:
            updates["university"] = provided_university
        if photo_url and is_safe_photo_url(photo_url) and not existing.get("photo_url"):
            updates["photo_url"] = photo_url
        if updates:
            user_ref.update(updates)

    return jsonify({"ok": True, "uid": uid, "email": email})


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash(tr("Logged out.", "Odhlásenie prebehlo úspešne."), "info")
    return redirect(url_for("main.index"))
