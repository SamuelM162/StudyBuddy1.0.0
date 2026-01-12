from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from firebase_admin import db as admin_db
from app.utils import login_required
from datetime import datetime

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


def make_thread_id(uid1, uid2):
    return "_".join(sorted([uid1, uid2]))


def update_last_seen(uid: str):
    """Uloží poslednú aktivitu používateľa pre online status."""
    try:
        admin_db.reference(f"presence/{uid}").set({"last_seen": datetime.utcnow().isoformat()})
    except Exception:
        # nechceme kvôli tomu zhodiť appku
        pass


@chat_bp.route("/inbox")
@login_required
def inbox():
    uid = session["user_id"]
    update_last_seen(uid)

    # user_threads/{uid}/{other_uid} -> {thread_id: "..."}
    user_threads = admin_db.reference(f"user_threads/{uid}").get() or {}
    users = admin_db.reference("users").get() or {}
    presence = admin_db.reference("presence").get() or {}

    threads = []

    for other_uid, info in (user_threads or {}).items():
        if not isinstance(info, dict):
            continue
        thread_id = info.get("thread_id")
        if not thread_id:
            continue

        user = users.get(other_uid, {}) or {}
        other_name = user.get("display_name") or user.get("email") or other_uid

        # správy v threade
        msgs_data = admin_db.reference(f"messages/{thread_id}").get() or {}
        msgs_list = list((msgs_data or {}).values())
        msgs_list.sort(key=lambda m: m.get("timestamp") or "")

        last = msgs_list[-1] if msgs_list else {}
        last_text = last.get("text", "")
        last_ts = last.get("timestamp", "")
        last_sender = last.get("sender_id")

        # unread count pre aktuálneho usera
        last_read_ts = admin_db.reference(f"last_read/{thread_id}/{uid}").get()
        unread_count = 0
        if msgs_list:
            for m in msgs_list:
                # nerátaj svoje správy
                if m.get("sender_id") == uid:
                    continue
                # ak nikdy nečítal, všetky cudzie správy sú unread
                if not last_read_ts or (m.get("timestamp") or "") > last_read_ts:
                    unread_count += 1

        # online/offline z presence
        p = presence.get(other_uid, {}) or {}
        last_seen = p.get("last_seen")
        is_online = False
        if last_seen:
            try:
                dt_last = datetime.fromisoformat(last_seen)
                delta = datetime.utcnow() - dt_last
                is_online = delta.total_seconds() < 120  # 2 minúty
            except Exception:
                is_online = False

        threads.append(
            {
                "other_uid": other_uid,
                "other_name": other_name,
                "last_text": last_text,
                "last_timestamp": last_ts,
                "last_sender": last_sender,
                "unread_count": unread_count,
                "is_online": is_online,
            }
        )

    # najnovšie hore
    threads.sort(key=lambda t: t["last_timestamp"] or "", reverse=True)

    return render_template("chat_inbox.html", threads=threads)


@chat_bp.route("/with/<other_uid>", methods=["GET", "POST"])
@login_required
def thread(other_uid):
    my_id = session["user_id"]
    my_email = session.get("email")
    update_last_seen(my_id)
    thread_id = make_thread_id(my_id, other_uid)

    blocked_me = admin_db.reference(f"blocks/{other_uid}/{my_id}").get()
    i_blocked = admin_db.reference(f"blocks/{my_id}/{other_uid}").get()

    # Ensure thread appears in my inbox even if it was created by the other side earlier.
    try:
        admin_db.reference(f"user_threads/{my_id}/{other_uid}").set({"thread_id": thread_id})
    except Exception:
        pass

    if request.method == "POST":
        if blocked_me or i_blocked:
            return redirect(url_for("chat.thread", other_uid=other_uid))
        text = request.form.get("text")
        if text:
            msg = {
                "sender_id": my_id,
                "sender_email": my_email,
                "text": text,
                "timestamp": datetime.utcnow().isoformat(),
            }
            admin_db.reference(f"messages/{thread_id}").push(msg)
            admin_db.reference(f"last_read/{thread_id}/{my_id}").set(msg["timestamp"])
            # stop typing indicator for sender
            try:
                admin_db.reference(f"typing/{thread_id}/{my_id}").delete()
            except Exception:
                pass
            # Only write under my own UID.
            try:
                admin_db.reference(f"user_threads/{my_id}/{other_uid}").set({"thread_id": thread_id})
            except Exception:
                pass
        return redirect(url_for("chat.thread", other_uid=other_uid))

    # načítaj správy
    messages_data = admin_db.reference(f"messages/{thread_id}").get() or {}
    messages = [m for _, m in messages_data.items()]
    messages.sort(key=lambda m: m.get("timestamp", ""))

    # označ thread ako prečítaný pre mňa – použijeme timestamp poslednej správy, ak existuje
    if messages:
        last_ts = messages[-1].get("timestamp") or datetime.utcnow().isoformat()
    else:
        last_ts = datetime.utcnow().isoformat()
    admin_db.reference(f"last_read/{thread_id}/{my_id}").set(last_ts)

    # last_read pre druhého účastníka – na "Seen" indikátor
    last_read_data = admin_db.reference(f"last_read/{thread_id}").get() or {}
    last_read_other = (last_read_data or {}).get(other_uid)

    # info o druhej strane
    other_profile = admin_db.reference(f"users/{other_uid}").get() or {}
    other_name = (
        other_profile.get("display_name")
        or other_profile.get("email")
        or other_uid
    )

    return render_template(
        "chat_thread.html",
        messages=messages,
        other_uid=other_uid,
        other_name=other_name,
        current_user_id=my_id,
        last_read_other=last_read_other,
    )


@chat_bp.route("/api/messages/<other_uid>")
@login_required
def api_messages(other_uid):
    my_id = session["user_id"]
    update_last_seen(my_id)
    thread_id = make_thread_id(my_id, other_uid)

    messages_data = admin_db.reference(f"messages/{thread_id}").get() or {}
    messages = []
    for _, m in messages_data.items():
        messages.append(
            {
                "sender_id": m.get("sender_id"),
                "sender_email": m.get("sender_email"),
                "text": m.get("text"),
                "timestamp": m.get("timestamp"),
            }
        )

    messages.sort(key=lambda m: m.get("timestamp") or "")

    if messages:
        last_ts = messages[-1].get("timestamp")
        if last_ts:
            admin_db.reference(f"last_read/{thread_id}/{my_id}").set(last_ts)

    # last_read pre druhého účastníka threadu – na "Seen" indikátor
    last_read_data = admin_db.reference(f"last_read/{thread_id}").get() or {}
    last_read_other = (last_read_data or {}).get(other_uid)

    return jsonify(
        {
            "messages": messages,
            "current_user_id": my_id,
            "last_read_other": last_read_other,
        }
    )


@chat_bp.route("/api/typing/<other_uid>", methods=["GET", "POST"])
@login_required
def typing_status(other_uid):
    my_id = session["user_id"]
    thread_id = make_thread_id(my_id, other_uid)

    if request.method == "POST":
        ts = datetime.utcnow().isoformat() if request.is_json and request.json.get("is_typing") else None
        try:
            if ts:
                admin_db.reference(f"typing/{thread_id}/{my_id}").set(ts)
            else:
                admin_db.reference(f"typing/{thread_id}/{my_id}").delete()
        except Exception:
            pass
        return jsonify({"ok": True})

    # GET – vrátime, či druhý user práve píše
    try:
        ts = admin_db.reference(f"typing/{thread_id}/{other_uid}").get()
        is_typing = False
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                is_typing = (datetime.utcnow() - dt).total_seconds() < 5
            except Exception:
                is_typing = False
    except Exception:
        is_typing = False

    return jsonify({"is_typing": bool(is_typing)})


# Route to delete a chat thread from the current user's inbox
@chat_bp.route("/delete/<other_uid>", methods=["POST"])
@login_required
def delete_thread(other_uid):
    my_id = session["user_id"]
    thread_id = make_thread_id(my_id, other_uid)

    # odstránime thread len z môjho inboxu (druhý user ho stále má)
    try:
        admin_db.reference(f"user_threads/{my_id}/{other_uid}").delete()
        admin_db.reference(f"last_read/{thread_id}/{my_id}").delete()
    except Exception:
        pass

    return redirect(url_for("chat.inbox"))