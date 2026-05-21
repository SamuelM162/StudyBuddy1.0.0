from datetime import datetime

from firebase_admin import db as admin_db
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.i18n import tr
from app.universities import is_valid_university
from app.utils import login_required, normalize_text


forum_bp = Blueprint("forum", __name__, url_prefix="/forum")

FORUM_CATEGORIES = [
    ("general", "General", "Všeobecné"),
    ("courses", "Courses", "Predmety"),
    ("exams", "Exams", "Skúšky"),
    ("admin", "Administration", "Administratíva"),
    ("events", "Events", "Podujatia"),
    ("housing", "Housing", "Bývanie"),
]


def _now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _sanitize_key(value: str) -> str:
    candidate = normalize_text(value, 120)
    if not candidate or any(char in candidate for char in "/.#$[]") or candidate in {".", ".."}:
        return ""
    return candidate


def _category_keys():
    return {key for key, _, _ in FORUM_CATEGORIES}


def _category_label(key: str) -> str:
    labels = {
        category_key: tr(en_label, sk_label)
        for category_key, en_label, sk_label in FORUM_CATEGORIES
    }
    return labels.get(key, labels["general"])


def _current_user_context():
    uid = session.get("user_id")
    profile = admin_db.reference(f"users/{uid}").get() or {}
    university = normalize_text(profile.get("university"), 120)
    display_name = (
        normalize_text(profile.get("display_name"), 120)
        or normalize_text(profile.get("email"), 120)
        or session.get("email")
        or tr("Student", "Študent")
    )

    return {
        "uid": uid,
        "profile": profile,
        "university": university,
        "has_valid_university": bool(university and is_valid_university(university)),
        "display_name": display_name,
    }


def _display_timestamp(value):
    if not value:
        return ""
    return str(value).replace("T", " ")[:16]


def _thread_is_visible(thread: dict, university: str) -> bool:
    return bool(thread and thread.get("university") == university and not thread.get("deleted"))


def _load_threads(university: str):
    users = admin_db.reference("users").get() or {}
    comments = admin_db.reference("institution_forum_comments").get() or {}
    raw_threads = admin_db.reference("institution_forum_threads").get() or {}
    threads = []

    if not isinstance(raw_threads, dict):
        return threads

    for thread_id, thread in raw_threads.items():
        if not _thread_is_visible(thread, university):
            continue

        author = users.get(thread.get("author_id"), {}) or {}
        thread_comments = comments.get(thread_id) or {}
        comment_count = len([
            comment
            for comment in thread_comments.values()
            if isinstance(comment, dict) and not comment.get("deleted")
        ]) if isinstance(thread_comments, dict) else int(thread.get("comment_count", 0) or 0)

        threads.append({
            "id": thread_id,
            "title": thread.get("title", ""),
            "body": thread.get("body", ""),
            "category": thread.get("category", "general"),
            "category_label": _category_label(thread.get("category", "general")),
            "author_id": thread.get("author_id", ""),
            "author_name": thread.get("author_name") or author.get("display_name") or author.get("email") or tr("Student", "Študent"),
            "score": int(thread.get("score", 0) or 0),
            "comment_count": comment_count,
            "created_at": thread.get("created_at", ""),
            "updated_at": thread.get("updated_at") or thread.get("created_at", ""),
            "created_at_display": _display_timestamp(thread.get("created_at")),
            "updated_at_display": _display_timestamp(thread.get("updated_at") or thread.get("created_at")),
        })

    return threads


@forum_bp.route("/")
@login_required
def forum_home():
    context = _current_user_context()
    sort = request.args.get("sort", "new")
    category = request.args.get("category", "all")

    threads = []
    if context["has_valid_university"]:
        threads = _load_threads(context["university"])

        if category != "all":
            threads = [thread for thread in threads if thread["category"] == category]

        if sort == "top":
            threads.sort(key=lambda item: (item["score"], item["comment_count"], item["updated_at"]), reverse=True)
        elif sort == "active":
            threads.sort(key=lambda item: (item["updated_at"], item["comment_count"]), reverse=True)
        else:
            sort = "new"
            threads.sort(key=lambda item: item["created_at"], reverse=True)

    return render_template(
        "forum_home.html",
        categories=FORUM_CATEGORIES,
        category=category,
        current_university=context["university"],
        missing_university=not context["has_valid_university"],
        sort=sort,
        threads=threads,
    )


@forum_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_thread():
    context = _current_user_context()
    if not context["has_valid_university"]:
        flash(tr("Set your university before posting in the institution forum.", "Pred pridaním príspevku do fóra si nastav univerzitu."), "warning")
        return redirect(url_for("profile.edit_profile"))

    if request.method == "POST":
        title = normalize_text(request.form.get("title"), 140)
        body = normalize_text(request.form.get("body"), 3000)
        category = normalize_text(request.form.get("category"), 32)
        if category not in _category_keys():
            category = "general"

        if not title or not body:
            flash(tr("Title and text are required.", "Názov a text sú povinné."), "danger")
            return redirect(url_for("forum.new_thread"))

        now = _now_iso()
        thread_ref = admin_db.reference("institution_forum_threads").push()
        thread_ref.set({
            "author_id": context["uid"],
            "author_name": context["display_name"],
            "body": body,
            "category": category,
            "comment_count": 0,
            "created_at": now,
            "deleted": False,
            "score": 1,
            "title": title,
            "university": context["university"],
            "updated_at": now,
        })
        admin_db.reference(f"institution_forum_votes/{thread_ref.key}/{context['uid']}").set(1)

        flash(tr("Thread created.", "Vlákno bolo vytvorené."), "success")
        return redirect(url_for("forum.thread_detail", thread_id=thread_ref.key))

    return render_template(
        "forum_new.html",
        categories=FORUM_CATEGORIES,
        current_university=context["university"],
    )


@forum_bp.route("/<thread_id>")
@login_required
def thread_detail(thread_id):
    context = _current_user_context()
    thread_id = _sanitize_key(thread_id)
    thread = admin_db.reference(f"institution_forum_threads/{thread_id}").get() or {}
    if not thread_id or not context["has_valid_university"] or not _thread_is_visible(thread, context["university"]):
        flash(tr("Thread not found in your institution forum.", "Vlákno sa vo fóre tvojej inštitúcie nenašlo."), "warning")
        return redirect(url_for("forum.forum_home"))

    users = admin_db.reference("users").get() or {}
    raw_comments = admin_db.reference(f"institution_forum_comments/{thread_id}").get() or {}
    votes = admin_db.reference(f"institution_forum_votes/{thread_id}").get() or {}
    comments = []

    if isinstance(raw_comments, dict):
        for comment_id, comment in raw_comments.items():
            if not isinstance(comment, dict) or comment.get("deleted"):
                continue
            author = users.get(comment.get("author_id"), {}) or {}
            comments.append({
                "id": comment_id,
                "author_id": comment.get("author_id", ""),
                "author_name": comment.get("author_name") or author.get("display_name") or author.get("email") or tr("Student", "Študent"),
                "body": comment.get("body", ""),
                "created_at": comment.get("created_at", ""),
                "created_at_display": _display_timestamp(comment.get("created_at")),
                "can_delete": comment.get("author_id") == context["uid"] or thread.get("author_id") == context["uid"],
            })
    comments.sort(key=lambda item: item["created_at"])

    author = users.get(thread.get("author_id"), {}) or {}
    thread_view = {
        "id": thread_id,
        "title": thread.get("title", ""),
        "body": thread.get("body", ""),
        "category": thread.get("category", "general"),
        "category_label": _category_label(thread.get("category", "general")),
        "author_id": thread.get("author_id", ""),
        "author_name": thread.get("author_name") or author.get("display_name") or author.get("email") or tr("Student", "Študent"),
        "score": int(thread.get("score", 0) or 0),
        "created_at_display": _display_timestamp(thread.get("created_at")),
        "updated_at_display": _display_timestamp(thread.get("updated_at") or thread.get("created_at")),
        "can_delete": thread.get("author_id") == context["uid"],
    }

    return render_template(
        "forum_thread.html",
        comments=comments,
        current_user_vote=int((votes or {}).get(context["uid"], 0) or 0) if isinstance(votes, dict) else 0,
        thread=thread_view,
    )


@forum_bp.route("/<thread_id>/comment", methods=["POST"])
@login_required
def add_comment(thread_id):
    context = _current_user_context()
    thread_id = _sanitize_key(thread_id)
    thread = admin_db.reference(f"institution_forum_threads/{thread_id}").get() or {}
    if not thread_id or not context["has_valid_university"] or not _thread_is_visible(thread, context["university"]):
        flash(tr("Thread not found in your institution forum.", "Vlákno sa vo fóre tvojej inštitúcie nenašlo."), "warning")
        return redirect(url_for("forum.forum_home"))

    body = normalize_text(request.form.get("body"), 2000)
    if not body:
        flash(tr("Comment cannot be empty.", "Komentár nemôže byť prázdny."), "danger")
        return redirect(url_for("forum.thread_detail", thread_id=thread_id))

    now = _now_iso()
    admin_db.reference(f"institution_forum_comments/{thread_id}").push({
        "author_id": context["uid"],
        "author_name": context["display_name"],
        "body": body,
        "created_at": now,
        "deleted": False,
    })

    comments = admin_db.reference(f"institution_forum_comments/{thread_id}").get() or {}
    comment_count = len([
        comment
        for comment in comments.values()
        if isinstance(comment, dict) and not comment.get("deleted")
    ]) if isinstance(comments, dict) else 1
    admin_db.reference(f"institution_forum_threads/{thread_id}").update({
        "comment_count": comment_count,
        "updated_at": now,
    })

    flash(tr("Comment added.", "Komentár bol pridaný."), "success")
    return redirect(url_for("forum.thread_detail", thread_id=thread_id))


@forum_bp.route("/<thread_id>/vote", methods=["POST"])
@login_required
def vote_thread(thread_id):
    context = _current_user_context()
    thread_id = _sanitize_key(thread_id)
    thread = admin_db.reference(f"institution_forum_threads/{thread_id}").get() or {}
    if not thread_id or not context["has_valid_university"] or not _thread_is_visible(thread, context["university"]):
        flash(tr("Thread not found in your institution forum.", "Vlákno sa vo fóre tvojej inštitúcie nenašlo."), "warning")
        return redirect(url_for("forum.forum_home"))

    direction = normalize_text(request.form.get("direction"), 8)
    vote_value = 1 if direction == "up" else -1 if direction == "down" else 0
    votes_ref = admin_db.reference(f"institution_forum_votes/{thread_id}")
    user_vote_ref = votes_ref.child(context["uid"])
    current_vote = int(user_vote_ref.get() or 0)

    if vote_value == current_vote:
        user_vote_ref.delete()
    elif vote_value:
        user_vote_ref.set(vote_value)

    votes = votes_ref.get() or {}
    score = sum(int(value or 0) for value in votes.values()) if isinstance(votes, dict) else 0
    admin_db.reference(f"institution_forum_threads/{thread_id}/score").set(score)

    return redirect(url_for("forum.thread_detail", thread_id=thread_id))


@forum_bp.route("/<thread_id>/delete", methods=["POST"])
@login_required
def delete_thread(thread_id):
    context = _current_user_context()
    thread_id = _sanitize_key(thread_id)
    thread_ref = admin_db.reference(f"institution_forum_threads/{thread_id}")
    thread = thread_ref.get() or {}
    if not thread_id or not context["has_valid_university"] or not _thread_is_visible(thread, context["university"]):
        flash(tr("Thread not found in your institution forum.", "Vlákno sa vo fóre tvojej inštitúcie nenašlo."), "warning")
        return redirect(url_for("forum.forum_home"))
    if thread.get("author_id") != context["uid"]:
        flash(tr("You can delete only your own thread.", "Môžeš odstrániť iba vlastné vlákno."), "danger")
        return redirect(url_for("forum.thread_detail", thread_id=thread_id))

    thread_ref.update({"deleted": True, "updated_at": _now_iso()})
    flash(tr("Thread deleted.", "Vlákno bolo odstránené."), "info")
    return redirect(url_for("forum.forum_home"))


@forum_bp.route("/<thread_id>/comments/<comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(thread_id, comment_id):
    context = _current_user_context()
    thread_id = _sanitize_key(thread_id)
    comment_id = _sanitize_key(comment_id)
    thread = admin_db.reference(f"institution_forum_threads/{thread_id}").get() or {}
    comment_ref = admin_db.reference(f"institution_forum_comments/{thread_id}/{comment_id}")
    comment = comment_ref.get() or {}

    if not thread_id or not comment_id or not context["has_valid_university"] or not _thread_is_visible(thread, context["university"]):
        flash(tr("Comment not found.", "Komentár sa nenašiel."), "warning")
        return redirect(url_for("forum.forum_home"))
    if comment.get("author_id") != context["uid"] and thread.get("author_id") != context["uid"]:
        flash(tr("You cannot delete this comment.", "Tento komentár nemôžeš odstrániť."), "danger")
        return redirect(url_for("forum.thread_detail", thread_id=thread_id))

    comment_ref.update({"deleted": True})
    comments = admin_db.reference(f"institution_forum_comments/{thread_id}").get() or {}
    comment_count = len([
        item
        for item in comments.values()
        if isinstance(item, dict) and not item.get("deleted")
    ]) if isinstance(comments, dict) else 0
    admin_db.reference(f"institution_forum_threads/{thread_id}").update({
        "comment_count": comment_count,
        "updated_at": _now_iso(),
    })

    flash(tr("Comment deleted.", "Komentár bol odstránený."), "info")
    return redirect(url_for("forum.thread_detail", thread_id=thread_id))
