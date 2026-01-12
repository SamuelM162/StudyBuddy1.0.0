from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.firebase_app import auth, db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        display_name = (request.form.get("display_name") or "").strip()

        try:
            user = auth.create_user_with_email_and_password(email, password)
        except Exception as e:
            flash(f"Registration failed: {e}", "danger")
            return render_template("auth_signup.html")

        uid = user["localId"]
        session["user_id"] = uid
        session["email"] = email

        db.child("users").child(uid).set({
            "email": email,
            "display_name": display_name if display_name else email,
            "faculty": "",
            "bio": "",
            "interests": [],
            "is_tutor": False
        })

        flash("Account created. Welcome to StudyBuddy!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth_signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            user = auth.sign_in_with_email_and_password(email, password)
        except Exception as e:
            flash(f"Login failed: {e}", "danger")
            return render_template("auth_login.html")

        uid = user["localId"]
        session["user_id"] = uid
        session["email"] = email

        user_ref = db.child("users").child(uid)
        existing = user_ref.get().val()

        if not existing:
            user_ref.set({
                "email": email,
                "display_name": email,
                "faculty": "",
                "bio": "",
                "interests": [],
                "is_tutor": False
            })

        flash("Logged in successfully.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth_login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("main.index"))
