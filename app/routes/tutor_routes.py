from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.firebase_app import db
from app.utils import login_required

tutor_bp = Blueprint("tutor", __name__, url_prefix="/tutor")

def _get_id_token():
    token = session.get("id_token") or session.get("idToken")
    if token is not None:
        token = str(token).strip()
    return token or None

@tutor_bp.route("/offers")
@login_required
def offers_list():
    current_uid = session["user_id"]
    token = _get_id_token()
    if not token:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    offers_data = db.child("tutor_offers").get(token=token).val() or {}
    offers = []
    for oid, o in offers_data.items():
        # NEzobrazuj moje vlastné ponuky v browse zozname
        if o.get("owner_id") == current_uid:
            continue

        o = o.copy()
        o["id"] = oid
        offers.append(o)

    return render_template("tutor_offers.html", offers=offers)

@tutor_bp.route("/offers/new", methods=["GET", "POST"])
@login_required
def new_offer():
    token = _get_id_token()
    if not token:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        subject = request.form.get("subject")
        description = request.form.get("description")
        rate = request.form.get("rate")
        uid = session["user_id"]
        email = session.get("email")

        data = {
            "owner_id": uid,
            "owner_email": email,
            "subject": subject,
            "description": description,
            "rate": rate
        }
        db.child("tutor_offers").push(data, token=token)
        flash("Tutoring offer created.", "success")
        return redirect(url_for("tutor.offers_list"))

    return render_template("tutor_offer_new.html")

@tutor_bp.route("/requests")
@login_required
def requests_list():
    token = _get_id_token()
    if not token:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    req_data = db.child("tutor_requests").get(token=token).val() or {}
    requests_list = []
    for rid, r in req_data.items():
        r["id"] = rid
        requests_list.append(r)
    return render_template("tutor_requests.html", requests=requests_list)

@tutor_bp.route("/requests/new", methods=["GET", "POST"])
@login_required
def new_request():
    token = _get_id_token()
    if not token:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        subject = request.form.get("subject")
        description = request.form.get("description")
        budget = request.form.get("budget")
        uid = session["user_id"]
        email = session.get("email")

        data = {
            "requester_id": uid,
            "requester_email": email,
            "subject": subject,
            "description": description,
            "budget": budget
        }
        db.child("tutor_requests").push(data, token=token)
        flash("Tutoring request created.", "success")
        return redirect(url_for("tutor.requests_list"))

    return render_template("tutor_request_new.html")
