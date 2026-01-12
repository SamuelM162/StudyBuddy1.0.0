import re
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.firebase_app import db
from app.utils import login_required

social_bp = Blueprint("social", __name__, url_prefix="/social")

def _extract_profile_interests(profile: dict) -> set:
    """Try to extract study interests/subjects from any reasonable keys in the profile.

    We intentionally support multiple possible field names because the profile
    form or DB structure may evolve (interests, study_interests, subjects, etc.).
    """
    if not profile:
        return set()

    # First, collect values from common/explicit keys
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

    # Additionally, scan all keys that look like they might contain subject/interest info
    for k, v in profile.items():
        kl = str(k).lower()
        if any(word in kl for word in ["interest", "subject", "course"]):
            if v not in candidate_values:
                candidate_values.append(v)

    # Reuse the normalizer to flatten list/dict/string
    merged = []
    for val in candidate_values:
        merged.append(val)
    # If nothing explicit was found, bail out
    if not merged:
        return set()

    return _normalize_interests(merged)

def _get_id_token():
    token = session.get("idToken") or session.get("id_token") or session.get("firebase_id_token") or session.get("token")
    if token is not None:
        token = str(token).strip()
    return token or None

def get_all_users():
    """Return all user profiles from /users (Admin SDK, no token needed)."""
    return db.child("users").get().val() or {}

def _normalize_interests(raw):
    """Convert whatever is stored as interests into a set of lowercase strings.

    Supports:
    - list / tuple / set
    - dict (values)
    - single string
    - stringified Python list: "['Math', 'Physics']"
    - comma/semicolon/slash separated strings
    """
    if not raw:
        return set()

    # Firebase may store interests as dict, list/tuple/set or a single string
    if isinstance(raw, dict):
        values = list(raw.values())
    elif isinstance(raw, (list, tuple, set)):
        values = list(raw)
    else:
        values = [raw]

    normalized = set()
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue

        # Special case: string that looks like a Python list, e.g. "['Math', 'Physics']"
        if s.startswith("[") and s.endswith("]") and "'" in s:
            items = re.findall(r"'([^']+)'", s)
            for item in items:
                p = item.strip().lower()
                if p:
                    normalized.add(p)
            continue

        # Normal case: comma/semicolon/slash separated values
        parts = re.split(r"[,;/]", s)
        for p in parts:
            p = p.strip().lower()
            if p:
                normalized.add(p)

    return normalized

@social_bp.route("/search")
@login_required
def search_users():
    q = request.args.get("q", "").lower()
    current_uid = session["user_id"]
    friends = db.child("friends").child(current_uid).get().val() or {}
    friend_ids = set(friends.keys())

    sent = db.child("friend_requests").child(current_uid).child("sent").get().val() or {}
    received = db.child("friend_requests").child(current_uid).child("received").get().val() or {}
    pending_ids = set(sent.keys()) | set(received.keys())

    users = get_all_users()
    results = []
    for uid, u in users.items():
        if uid == current_uid:
            continue
        name = (u.get("display_name") or "").lower()
        faculty = (u.get("faculty") or "").lower()
        interests_set = _extract_profile_interests(u)
        interests = " ".join(interests_set)
        if q in name or q in faculty or q in interests:
            tmp = u.copy()
            tmp["uid"] = uid
            if uid in friend_ids:
                tmp["relation"] = "friend"
            elif uid in pending_ids:
                tmp["relation"] = "pending"
            else:
                tmp["relation"] = "none"
            results.append(tmp)
    return render_template("social_search.html", query=q, results=results)

@social_bp.route("/suggestions")
@login_required
def suggestions():
    current_uid = session["user_id"]
    current_profile = db.child("users").child(current_uid).get().val() or {}

    # Try to extract study interests/subjects from the current profile
    current_interests = _extract_profile_interests(current_profile)

    friends = db.child("friends").child(current_uid).get().val() or {}
    friend_ids = set(friends.keys())

    sent = db.child("friend_requests").child(current_uid).child("sent").get().val() or {}
    received = db.child("friend_requests").child(current_uid).child("received").get().val() or {}
    pending_ids = set(sent.keys()) | set(received.keys())

    users = get_all_users()
    suggestions_list = []

    for uid, u in users.items():
        if uid == current_uid:
            continue
        if uid in friend_ids or uid in pending_ids:
            continue
        # For other users, also support multiple possible keys / flexible extraction
        other_interests = _extract_profile_interests(u)
        shared = current_interests & other_interests
        if shared:
            suggestions_list.append({
                "uid": uid,
                "display_name": u.get("display_name") or u.get("email"),
                "faculty": u.get("faculty", ""),
                "interests": u.get("interests", []),
                "shared_count": len(shared),
                "shared_list": list(shared)
            })

    suggestions_list.sort(key=lambda x: x["shared_count"], reverse=True)
    return render_template("social_suggestions.html", suggestions=suggestions_list)

@social_bp.route("/friends")
@login_required
def friends_list():
    current_uid = session["user_id"]

    # všetci používatelia (profily)
    users = get_all_users() or {}

    # zoznam priateľov
    friends_raw = db.child("friends").child(current_uid).get().val() or {}
    friend_objs = []
    for fid in friends_raw.keys():
        u = users.get(fid) or {}
        if u:
            friend_objs.append({
                "uid": fid,
                "display_name": u.get("display_name") or u.get("email", fid),
                "faculty": u.get("faculty", ""),
                "interests": u.get("interests", []),
            })

    # friend requests (prijaté / odoslané)
    received_raw = db.child("friend_requests").child(current_uid).child("received").get().val() or {}
    sent_raw = db.child("friend_requests").child(current_uid).child("sent").get().val() or {}

    received_requests = []
    for from_uid in received_raw.keys():
        u = users.get(from_uid) or {}
        received_requests.append({
            "uid": from_uid,
            "display_name": u.get("display_name") or u.get("email", from_uid),
        })

    sent_requests = []
    for to_uid in sent_raw.keys():
        u = users.get(to_uid) or {}
        sent_requests.append({
            "uid": to_uid,
            "display_name": u.get("display_name") or u.get("email", to_uid),
        })

    return render_template(
        "social_friends.html",
        friends=friend_objs,
        received_requests=received_requests,
        sent_requests=sent_requests,
    )

@social_bp.route("/block/<uid>")
@login_required
def block_user(uid):
    current_uid = session["user_id"]
    if uid == current_uid:
        return redirect(url_for("social.friends_list"))

    # mark that current user blocks this uid
    db.child("blocks").child(current_uid).child(uid).set(True)
    flash("User has been blocked. They will no longer be able to message you.", "info")
    return redirect(url_for("social.friends_list"))


@social_bp.route("/unblock/<uid>")
@login_required
def unblock_user(uid):
    current_uid = session["user_id"]
    if uid == current_uid:
        return redirect(url_for("social.friends_list"))

    db.child("blocks").child(current_uid).child(uid).remove()
    flash("User has been unblocked.", "info")
    return redirect(url_for("social.friends_list"))

@social_bp.route("/request/<target_uid>")
@login_required
def send_request(target_uid):
    current_uid = session["user_id"]
    if target_uid == current_uid:
        return redirect(url_for("social.friends_list"))

    db.child("friend_requests").child(current_uid).child("sent").child(target_uid).set(True)
    db.child("friend_requests").child(target_uid).child("received").child(current_uid).set(True)
    flash("Friend request sent.", "success")
    return redirect(url_for("social.friends_list"))

@social_bp.route("/accept/<from_uid>")
@login_required
def accept_request(from_uid):
    current_uid = session["user_id"]

    db.child("friends").child(current_uid).child(from_uid).set(True)
    db.child("friends").child(from_uid).child(current_uid).set(True)

    db.child("friend_requests").child(current_uid).child("received").child(from_uid).remove()
    db.child("friend_requests").child(from_uid).child("sent").child(current_uid).remove()

    flash("Friend request accepted.", "success")
    return redirect(url_for("social.friends_list"))

@social_bp.route("/decline/<from_uid>")
@login_required
def decline_request(from_uid):
    current_uid = session["user_id"]
    db.child("friend_requests").child(current_uid).child("received").child(from_uid).remove()
    db.child("friend_requests").child(from_uid).child("sent").child(current_uid).remove()
    flash("Friend request declined.", "info")
    return redirect(url_for("social.friends_list"))
