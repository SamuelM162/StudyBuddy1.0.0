from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.firebase_app import db
from app.i18n import tr
from app.utils import login_required, normalize_text

tutor_bp = Blueprint("tutor", __name__, url_prefix="/tutor")

@tutor_bp.route("/offers")
@login_required
def offers_list():
    current_uid = session["user_id"]

    offers_data = db.child("tutor_offers").get().val() or {}
    offers = []
    for oid, o in offers_data.items():
        # NEzobrazuj moje vlastné ponuky v browse zozname
        if o.get("owner_id") == current_uid:
            continue

        o = o.copy()
        o["id"] = oid
        offers.append(o)

    return render_template("tutor_offers.html", offers=offers)

@tutor_bp.route("/offers/mine")
@login_required
def my_offers():
    current_uid = session["user_id"]

    offers_data = db.child("tutor_offers").get().val() or {}
    my_offers = []

    for oid, o in offers_data.items():
        if o.get("owner_id") != current_uid:
            continue

        o = o.copy()
        o["id"] = oid
        my_offers.append(o)

    return render_template("tutor_offers.html", offers=my_offers, my_view=True)

@tutor_bp.route("/offers/new", methods=["GET", "POST"])
@login_required
def new_offer():
    if request.method == "POST":
        subject = normalize_text(request.form.get("subject"), 120)
        description = normalize_text(request.form.get("description"), 500)
        rate = normalize_text(request.form.get("rate"), 80)
        uid = session["user_id"]
        email = session.get("email")

        if not subject or not description:
            flash(tr("Subject and description are required.", "Predmet a popis sú povinné."), "danger")
            return redirect(url_for("tutor.new_offer"))

        data = {
            "owner_id": uid,
            "owner_email": email,
            "subject": subject,
            "description": description,
            "rate": rate
        }
        db.child("tutor_offers").push(data)
        flash(tr("Tutoring offer created.", "Ponuka doučovania bola vytvorená."), "success")
        return redirect(url_for("tutor.offers_list"))

    return render_template("tutor_offer_new.html")

@tutor_bp.route("/requests")
@login_required
def requests_list():
    req_data = db.child("tutor_requests").get().val() or {}
    requests_list = []
    for rid, r in req_data.items():
        r["id"] = rid
        requests_list.append(r)
    return render_template("tutor_requests.html", requests=requests_list)

@tutor_bp.route("/requests/new", methods=["GET", "POST"])
@login_required
def new_request():
    if request.method == "POST":
        subject = normalize_text(request.form.get("subject"), 120)
        description = normalize_text(request.form.get("description"), 500)
        budget = normalize_text(request.form.get("budget"), 80)
        uid = session["user_id"]
        email = session.get("email")

        if not subject or not description:
            flash(tr("Subject and description are required.", "Predmet a popis sú povinné."), "danger")
            return redirect(url_for("tutor.new_request"))

        data = {
            "requester_id": uid,
            "requester_email": email,
            "subject": subject,
            "description": description,
            "budget": budget
        }
        db.child("tutor_requests").push(data)
        flash(tr("Tutoring request created.", "Žiadosť o doučovanie bola vytvorená."), "success")
        return redirect(url_for("tutor.requests_list"))

    return render_template("tutor_request_new.html")

@tutor_bp.route("/offers/delete/<offer_id>", methods=["POST"])
@login_required
def delete_offer(offer_id):
    current_uid = session["user_id"]

    offer = db.child("tutor_offers").child(offer_id).get().val()
    if not offer:
        flash(tr("Offer not found.", "Ponuka sa nenašla."), "error")
        return redirect(url_for("tutor.my_offers"))

    if offer.get("owner_id") != current_uid:
        flash(tr("You are not allowed to delete this offer.", "Nemáte oprávnenie odstrániť túto ponuku."), "error")
        return redirect(url_for("tutor.my_offers"))

    db.child("tutor_offers").child(offer_id).remove()
    flash(tr("Offer deleted.", "Ponuka bola odstránená."), "success")
    return redirect(url_for("tutor.my_offers"))
