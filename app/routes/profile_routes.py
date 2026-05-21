from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from firebase_admin import db as admin_db
from app.i18n import tr
from app.universities import is_valid_university
from app.utils import is_safe_photo_url, login_required, normalize_text, parse_interests

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/me", methods=["GET", "POST"])
@login_required
def edit_profile():
    # vytiahneme info zo session
    uid = (session.get("user_id") or "").strip()
    email = (session.get("email") or "").strip()

    if (not uid) or uid == "/" or "/" in uid:
        flash(tr("Session expired. Please log in again.", "Relácia vypršala. Prihláste sa znova."), "warning")
        return redirect(url_for("auth.login"))

    user_ref = admin_db.reference(f"users/{uid}")
    current = user_ref.get() or {}

    if not current:
        user_ref.set({
            "email": email,
            "display_name": email,
            "faculty": "",
            "university": "",
            "bio": "",
            "interests": [],
            "photo_url": "",
            "is_tutor": False,
        })
        current = user_ref.get() or {}

    if request.method == "POST":
        display_name = normalize_text(request.form.get("display_name"), 80)
        faculty = normalize_text(request.form.get("faculty"), 120)
        university = normalize_text(request.form.get("university"), 120)
        bio = normalize_text(request.form.get("bio"), 280)
        interests_raw = request.form.get("interests", "")
        photo_url = normalize_text(request.form.get("photo_url"), 500)
        is_tutor = bool(request.form.get("is_tutor"))
        interests = parse_interests(interests_raw)
        errors = []

        if university and not is_valid_university(university):
            errors.append(tr("Please select a valid university.", "Vyberte platnú univerzitu."))
        if photo_url and not is_safe_photo_url(photo_url):
            errors.append(tr("Profile photo URL must start with http:// or https://.", "URL profilovej fotky musí začínať na http:// alebo https://."))

        if errors:
            for error in errors:
                flash(error, "danger")
            profile = current
            profile.update({
                "display_name": display_name,
                "faculty": faculty,
                "university": university,
                "bio": bio,
                "interests": interests,
                "photo_url": photo_url,
                "is_tutor": is_tutor,
            })
            return render_template("profile_edit.html", profile=profile, interests_str=", ".join(interests))

        update_data = {
            "display_name": display_name or current.get("display_name") or email or "Student",
            "faculty": faculty,
            "university": university,
            "bio": bio,
            "photo_url": photo_url,
            "interests": interests,
            "is_tutor": is_tutor,
        }

        # email zachováme – buď zo session alebo z profilu
        update_data["email"] = email or current.get("email", "")

        # uložíme len aktualizované polia pod /users/<uid>
        user_ref.update(update_data)

        flash(tr("Profile updated.", "Profil bol aktualizovaný."), "success")
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
        flash(tr("User not found.", "Používateľ sa nenašiel."), "warning")
        return redirect(url_for("main.dashboard"))
    profile = admin_db.reference(f"users/{uid}").get()
    if not profile:
        flash(tr("User not found.", "Používateľ sa nenašiel."), "warning")
        return redirect(url_for("main.dashboard"))
    return render_template("profile_view.html", profile=profile, uid=uid, current_uid=session.get("user_id"))
