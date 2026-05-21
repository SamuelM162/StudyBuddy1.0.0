import re
from typing import Dict, List

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from firebase_admin import db as admin_db

from app.i18n import get_return_path, tr
from app.universities import is_valid_university
from app.utils import login_required, normalize_text

social_bp = Blueprint("social", __name__, url_prefix="/social")


def _sanitize_uid(uid: str) -> str:
    value = (uid or "").strip()
    if not value or value == "/" or "/" in value:
        return ""
    return value


def _get_id_set(path: str) -> set:
    raw = admin_db.reference(path).get() or {}
    if not isinstance(raw, dict):
        return set()
    return {key for key in raw.keys() if key}


def _get_current_uid() -> str:
    return _sanitize_uid(session.get("user_id"))


def _normalize_interests(raw):
    if not raw:
        return set()

    if isinstance(raw, dict):
        values = list(raw.values())
    elif isinstance(raw, (list, tuple, set)):
        values = list(raw)
    else:
        values = [raw]

    normalized = set()
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue

        if text.startswith("[") and text.endswith("]") and "'" in text:
            items = re.findall(r"'([^']+)'", text)
            for item in items:
                cleaned = item.strip().lower()
                if cleaned:
                    normalized.add(cleaned)
            continue

        for item in re.split(r"[,;/]", text):
            cleaned = item.strip().lower()
            if cleaned:
                normalized.add(cleaned)

    return normalized


def _extract_profile_interests(profile: dict) -> set:
    if not profile:
        return set()

    candidate_values = []
    for key in [
        "interests",
        "study_interests",
        "subjects",
        "study_subjects",
        "subject_interests",
    ]:
        if key in profile and profile.get(key):
            candidate_values.append(profile.get(key))

    for key, value in profile.items():
        key_lower = str(key).lower()
        if any(word in key_lower for word in ["interest", "subject", "course"]) and value not in candidate_values:
            candidate_values.append(value)

    if not candidate_values:
        return set()

    return _normalize_interests(candidate_values)


def get_all_users():
    return admin_db.reference("users").get() or {}


def _user_exists(uid: str) -> bool:
    clean_uid = _sanitize_uid(uid)
    if not clean_uid:
        return False
    return bool(admin_db.reference(f"users/{clean_uid}").get())


def _build_user_card(uid: str, profile: dict, relation: str = "none") -> dict:
    interests = profile.get("interests") or []
    if isinstance(interests, dict):
        interests = list(interests.values())
    elif not isinstance(interests, list):
        interests = [str(interests)] if interests else []

    return {
        "uid": uid,
        "display_name": profile.get("display_name") or profile.get("email") or uid,
        "email": profile.get("email", ""),
        "faculty": profile.get("faculty", ""),
        "university": profile.get("university", ""),
        "bio": profile.get("bio", ""),
        "interests": interests,
        "photo_url": profile.get("photo_url", ""),
        "relation": relation,
    }


def _sort_users(items: List[Dict]) -> List[Dict]:
    return sorted(items, key=lambda item: (item.get("display_name") or "").lower())


def _relationship_sets(current_uid: str):
    friend_ids = _get_id_set(f"friends/{current_uid}")
    sent_ids = _get_id_set(f"friend_requests/{current_uid}/sent")
    received_ids = _get_id_set(f"friend_requests/{current_uid}/received")
    pending_ids = sent_ids | received_ids
    return friend_ids, sent_ids, received_ids, pending_ids


@social_bp.route("/search")
@login_required
def search_users():
    raw_query = normalize_text(request.args.get("q"), 80)
    query = raw_query.lower()
    current_uid = _get_current_uid()
    friend_ids, _, _, pending_ids = _relationship_sets(current_uid)

    users = get_all_users()
    results = []
    for uid, profile in users.items():
        if uid == current_uid:
            continue
        name = (profile.get("display_name") or "").lower()
        faculty = (profile.get("faculty") or "").lower()
        university = (profile.get("university") or "").lower()
        interests = " ".join(_extract_profile_interests(profile))
        if not query or query in name or query in faculty or query in university or query in interests:
            relation = "friend" if uid in friend_ids else "pending" if uid in pending_ids else "none"
            results.append(_build_user_card(uid, profile, relation=relation))

    return render_template("social_search.html", query=raw_query, results=_sort_users(results))


@social_bp.route("/suggestions")
@login_required
def suggestions():
    current_uid = _get_current_uid()
    current_profile = admin_db.reference(f"users/{current_uid}").get() or {}
    current_interests = _extract_profile_interests(current_profile)
    friend_ids, _, _, pending_ids = _relationship_sets(current_uid)

    users = get_all_users()
    suggestions_list = []

    for uid, profile in users.items():
        if uid == current_uid or uid in friend_ids or uid in pending_ids:
            continue

        other_interests = _extract_profile_interests(profile)
        shared = sorted(current_interests & other_interests)
        if shared:
            item = _build_user_card(uid, profile)
            item["shared_count"] = len(shared)
            item["shared_list"] = shared
            suggestions_list.append(item)

    suggestions_list.sort(key=lambda item: (-item["shared_count"], item["display_name"].lower()))
    return render_template("social_suggestions.html", suggestions=suggestions_list)


@social_bp.route("/friends")
@login_required
def friends_list():
    current_uid = _get_current_uid()
    users = get_all_users() or {}

    friend_ids, sent_ids, received_ids, _ = _relationship_sets(current_uid)

    friends = _sort_users([
        _build_user_card(uid, users.get(uid) or {}, relation="friend")
        for uid in friend_ids
        if users.get(uid)
    ])
    received_requests = _sort_users([
        _build_user_card(uid, users.get(uid) or {}, relation="pending")
        for uid in received_ids
        if users.get(uid)
    ])
    sent_requests = _sort_users([
        _build_user_card(uid, users.get(uid) or {}, relation="pending")
        for uid in sent_ids
        if users.get(uid)
    ])

    return render_template(
        "social_friends.html",
        friends=friends,
        received_requests=received_requests,
        sent_requests=sent_requests,
    )


@social_bp.route("/institution")
@login_required
def institution_view():
    current_uid = _get_current_uid()
    current_profile = admin_db.reference(f"users/{current_uid}").get() or {}
    current_university = normalize_text(current_profile.get("university"), 120)
    friend_ids, _, _, pending_ids = _relationship_sets(current_uid)

    members = []
    if current_university and is_valid_university(current_university):
        for uid, profile in (get_all_users() or {}).items():
            if uid == current_uid:
                continue
            if normalize_text(profile.get("university"), 120) != current_university:
                continue
            relation = "friend" if uid in friend_ids else "pending" if uid in pending_ids else "none"
            members.append(_build_user_card(uid, profile, relation=relation))

    return render_template(
        "social_institution.html",
        current_university=current_university,
        members=_sort_users(members),
        missing_university=not current_university or not is_valid_university(current_university),
    )


@social_bp.route("/api/block/<uid>", methods=["POST"])
@login_required
def api_block_toggle(uid):
    current_uid = _get_current_uid()
    target_uid = _sanitize_uid(uid)
    if not target_uid or target_uid == current_uid:
        return jsonify({"ok": False, "error": "cannot_block_self"}), 400

    ref = admin_db.reference(f"blocks/{current_uid}/{target_uid}")
    currently_blocked = ref.get() is not None

    if currently_blocked:
        ref.delete()
        blocked_now = False
    else:
        ref.set(True)
        blocked_now = True

    return jsonify({"ok": True, "blocked": blocked_now})


@social_bp.route("/api/is_blocked/<uid>", methods=["GET"])
@login_required
def api_is_blocked(uid):
    current_uid = _get_current_uid()
    target_uid = _sanitize_uid(uid)

    if not target_uid or target_uid == current_uid:
        return jsonify({"ok": True, "blocked": False})

    blocked = admin_db.reference(f"blocks/{current_uid}/{target_uid}").get() is not None
    return jsonify({"ok": True, "blocked": bool(blocked)})


@social_bp.route("/block/<uid>")
@login_required
def block_user(uid):
    current_uid = _get_current_uid()
    target_uid = _sanitize_uid(uid)
    if not target_uid or target_uid == current_uid:
        return redirect(url_for("social.friends_list"))

    admin_db.reference(f"blocks/{current_uid}/{target_uid}").set(True)
    flash(tr("User has been blocked. They will no longer be able to message you.", "Používateľ bol zablokovaný. Už vám nebude môcť písať."), "info")
    return redirect(url_for("social.friends_list"))


@social_bp.route("/unblock/<uid>")
@login_required
def unblock_user(uid):
    current_uid = _get_current_uid()
    target_uid = _sanitize_uid(uid)
    if not target_uid or target_uid == current_uid:
        return redirect(url_for("social.friends_list"))

    admin_db.reference(f"blocks/{current_uid}/{target_uid}").delete()
    flash(tr("User has been unblocked.", "Používateľ bol odblokovaný."), "info")
    return redirect(url_for("social.friends_list"))


@social_bp.route("/request/<target_uid>", methods=["POST"])
@login_required
def send_request(target_uid):
    current_uid = _get_current_uid()
    target_uid = _sanitize_uid(target_uid)

    if not target_uid or target_uid == current_uid:
        flash(tr("You cannot add yourself.", "Nemôžete si poslať žiadosť sami sebe."), "warning")
        return redirect(url_for("social.search_users"))
    if not _user_exists(target_uid):
        flash(tr("User not found.", "Používateľ sa nenašiel."), "warning")
        return redirect(url_for("social.search_users"))

    friend_ids, sent_ids, received_ids, pending_ids = _relationship_sets(current_uid)
    if target_uid in friend_ids:
        flash(tr("You are already friends.", "Už ste priatelia."), "info")
        return redirect(url_for("social.friends_list"))
    if target_uid in pending_ids:
        if target_uid in received_ids:
            flash(tr("This user already sent you a request. Accept it from your requests list.", "Tento používateľ vám už poslal žiadosť. Prijmite ju v zozname žiadostí."), "info")
        else:
            flash(tr("Friend request already pending.", "Žiadosť o priateľstvo už čaká na vybavenie."), "info")
        return redirect(get_return_path())

    if admin_db.reference(f"blocks/{current_uid}/{target_uid}").get():
        flash(tr("Unblock this user before sending a request.", "Pred odoslaním žiadosti musíte tohto používateľa odblokovať."), "warning")
        return redirect(get_return_path())
    if admin_db.reference(f"blocks/{target_uid}/{current_uid}").get():
        flash(tr("You cannot send a request to this user right now.", "Tomuto používateľovi teraz nemôžete poslať žiadosť."), "warning")
        return redirect(get_return_path())

    admin_db.reference(f"friend_requests/{current_uid}/sent/{target_uid}").set(True)
    admin_db.reference(f"friend_requests/{target_uid}/received/{current_uid}").set(True)
    flash(tr("Friend request sent.", "Žiadosť o priateľstvo bola odoslaná."), "success")
    return redirect(get_return_path())


@social_bp.route("/accept/<from_uid>", methods=["POST"])
@login_required
def accept_request(from_uid):
    current_uid = _get_current_uid()
    from_uid = _sanitize_uid(from_uid)

    if not from_uid or from_uid == current_uid:
        flash(tr("Invalid friend request.", "Neplatná žiadosť o priateľstvo."), "warning")
        return redirect(url_for("social.friends_list"))

    if from_uid not in _get_id_set(f"friend_requests/{current_uid}/received"):
        flash(tr("Friend request not found.", "Žiadosť o priateľstvo sa nenašla."), "warning")
        return redirect(url_for("social.friends_list"))

    admin_db.reference(f"friends/{current_uid}/{from_uid}").set(True)
    admin_db.reference(f"friends/{from_uid}/{current_uid}").set(True)
    admin_db.reference(f"friend_requests/{current_uid}/received/{from_uid}").delete()
    admin_db.reference(f"friend_requests/{from_uid}/sent/{current_uid}").delete()

    flash(tr("Friend request accepted.", "Žiadosť o priateľstvo bola prijatá."), "success")
    return redirect(url_for("social.friends_list"))


@social_bp.route("/decline/<from_uid>", methods=["POST"])
@login_required
def decline_request(from_uid):
    current_uid = _get_current_uid()
    from_uid = _sanitize_uid(from_uid)

    if not from_uid or from_uid == current_uid:
        flash(tr("Invalid friend request.", "Neplatná žiadosť o priateľstvo."), "warning")
        return redirect(url_for("social.friends_list"))

    if from_uid not in _get_id_set(f"friend_requests/{current_uid}/received"):
        flash(tr("Friend request not found.", "Žiadosť o priateľstvo sa nenašla."), "warning")
        return redirect(url_for("social.friends_list"))

    admin_db.reference(f"friend_requests/{current_uid}/received/{from_uid}").delete()
    admin_db.reference(f"friend_requests/{from_uid}/sent/{current_uid}").delete()
    flash(tr("Friend request declined.", "Žiadosť o priateľstvo bola odmietnutá."), "info")
    return redirect(url_for("social.friends_list"))
