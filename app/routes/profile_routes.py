from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.firebase_app import db
from app.utils import login_required

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/me", methods=["GET", "POST"])
@login_required
def edit_profile():
    # vytiahneme info zo session
    uid = (session.get("user_id") or "").strip()
    email = (session.get("email") or "").strip()

    if (not uid) or uid == "/" or "/" in uid:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    user_ref = db.child("users").child(uid)
    current = user_ref.get().val() or {}

    if not current:
        user_ref.set({
            "email": email,
            "display_name": email,
            "faculty": "",
            "bio": "",
            "interests": [],
            "is_tutor": False,
        })
        current = user_ref.get().val() or {}

    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        faculty = request.form.get("faculty", "").strip()
        bio = request.form.get("bio", "").strip()
        interests_raw = request.form.get("interests", "")
        is_tutor = bool(request.form.get("is_tutor"))

        # z textu "Math, Programming 1" spravíme list
        interests = [s.strip() for s in interests_raw.split(",") if s.strip()]

        update_data = {
            "display_name": display_name,
            "faculty": faculty,
            "bio": bio,
            "is_tutor": is_tutor,
        }

        # email zachováme – buď zo session alebo z profilu
        update_data["email"] = email or current.get("email", "")

        if interests:
            update_data["interests"] = interests

        # uložíme len aktualizované polia pod /users/<uid>
        user_ref.update(update_data)

        flash("Profile updated.", "success")
        return redirect(url_for("profile.view_profile", uid=uid))

    # GET – pripravíme data pre formulár
    profile = current
    interests_list = profile.get("interests") or []
    if isinstance(interests_list, list):
        interests_str = ", ".join(interests_list)
    else:
        interests_str = str(interests_list)

    return render_template("profile_edit.html", profile=profile, interests_str=interests_str)


@profile_bp.route("/view/<uid>")
@login_required
def view_profile(uid):
    uid = (uid or "").strip()
    if (not uid) or uid == "/" or "/" in uid:
        flash("User not found.", "warning")
        return redirect(url_for("main.dashboard"))
    profile = db.child("users").child(uid).get().val()
    if not profile:
        flash("User not found.", "warning")
        return redirect(url_for("main.dashboard"))
    return render_template("profile_view.html", profile=profile, uid=uid)