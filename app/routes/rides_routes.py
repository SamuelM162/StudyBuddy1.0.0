from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.utils import login_required
from app.firebase_app import db

rides_bp = Blueprint("rides", __name__, url_prefix="/rides")


@rides_bp.route("/", methods=["GET"])
@login_required
def rides_list():
    """List rides with seat info and flags for the current user.

    Supports:
      - /rides/           -> all rides
      - /rides/?mine=1    -> only my rides (driver_id == current user)
    """
    uid = session.get("user_id")
    if not uid:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    rides_raw = db.child("rides").get().val() or {}
    passengers_raw = db.child("ride_passengers").get().val() or {}

    if not isinstance(rides_raw, dict):
        rides_raw = {}
    if not isinstance(passengers_raw, dict):
        passengers_raw = {}

    mine = request.args.get("mine") in ("1", "true", "yes", "on")

    rides = []
    for ride_id, ride in (rides_raw or {}).items():
        if not ride:
            continue

        if mine and ride.get("driver_id") != uid:
            continue

        ride_passengers = passengers_raw.get(ride_id) or {}
        if not isinstance(ride_passengers, dict):
            ride_passengers = {}

        seats_total = int(ride.get("seats_total", 0) or 0)
        seats_taken = len(ride_passengers)
        seats_left = max(0, seats_total - seats_taken)

        is_driver = ride.get("driver_id") == uid
        is_passenger = uid in ride_passengers
        is_full = seats_total > 0 and seats_taken >= seats_total

        rides.append({
            "id": ride_id,
            "driver_id": ride.get("driver_id", ""),
            "from_location": ride.get("from_location", ""),
            "to_location": ride.get("to_location", ""),
            "departure_time": ride.get("departure_time", ""),
            "seats_total": seats_total,
            "seats_taken": seats_taken,
            "seats_left": seats_left,
            "status": ride.get("status", "active"),
            "notes": ride.get("notes", ""),
            "contribution": ride.get("contribution", ""),
            "is_driver": is_driver,
            "is_passenger": is_passenger,
            "is_full": is_full,
        })

    return render_template("rides_list.html", rides=rides, mine=mine)


@rides_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_ride():
    """Create a new ride as the current user (driver)."""
    uid = session.get("user_id")
    if not uid:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        from_location = request.form.get("from_location", "").strip()
        to_location = request.form.get("to_location", "").strip()
        departure_time = request.form.get("departure_time", "").strip()
        seats_total = request.form.get("seats_total", "").strip()
        contribution = request.form.get("contribution", "").strip()
        notes = request.form.get("notes", "").strip()

        errors = []
        if not from_location:
            errors.append("From location is required.")
        if not to_location:
            errors.append("To location is required.")
        if not seats_total or not seats_total.isdigit():
            errors.append("Seats must be a number.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return redirect(url_for("rides.new_ride"))

        seats_total_i = int(seats_total)

        ride_data = {
            "driver_id": uid,
            "from_location": from_location,
            "to_location": to_location,
            "departure_time": departure_time,
            "seats_total": seats_total_i,
            "contribution": contribution,
            "notes": notes,
            "status": "active",
        }

        db.child("rides").push(ride_data)
        flash("Ride created successfully.", "success")
        return redirect(url_for("rides.rides_list"))

    return render_template("ride_new.html")


@rides_bp.route("/join/<ride_id>", methods=["POST"])
@login_required
def join_ride(ride_id):
    """Join a ride as a passenger."""
    uid = session.get("user_id")
    if not uid:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    ride = db.child("rides").child(ride_id).get().val() or {}
    if not ride:
        flash("Ride not found.", "warning")
        return redirect(url_for("rides.rides_list"))

    if ride.get("driver_id") == uid:
        flash("You cannot join your own ride as a passenger.", "info")
        return redirect(url_for("rides.rides_list"))

    seats_total = int(ride.get("seats_total", 0) or 0)

    passengers = db.child("ride_passengers").child(ride_id).get().val() or {}
    if not isinstance(passengers, dict):
        passengers = {}

    seats_taken = len(passengers)

    if uid in passengers:
        flash("You have already joined this ride.", "info")
        return redirect(url_for("rides.rides_list"))

    if seats_total > 0 and seats_taken >= seats_total:
        flash("This ride is already full.", "warning")
        return redirect(url_for("rides.rides_list"))

    db.child("ride_passengers").child(ride_id).child(uid).set(True)
    flash("You joined this ride.", "success")
    return redirect(url_for("rides.rides_list"))


@rides_bp.route("/leave/<ride_id>", methods=["POST"])
@login_required
def leave_ride(ride_id):
    """Leave a ride where the current user is a passenger."""
    uid = session.get("user_id")
    if not uid:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    ride = db.child("rides").child(ride_id).get().val() or {}
    if not ride:
        flash("Ride not found.", "warning")
        return redirect(url_for("rides.rides_list"))

    passengers = db.child("ride_passengers").child(ride_id).get().val() or {}
    if not isinstance(passengers, dict):
        passengers = {}

    if uid not in passengers:
        flash("You are not a passenger on this ride.", "info")
        return redirect(url_for("rides.rides_list"))

    db.child("ride_passengers").child(ride_id).child(uid).remove()
    flash("You left this ride.", "success")
    return redirect(url_for("rides.rides_list"))


@rides_bp.route("/cancel/<ride_id>", methods=["POST"])
@login_required
def cancel_ride(ride_id):
    """Cancel (delete) a ride as the driver only."""
    uid = session.get("user_id")
    if not uid:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    ride_ref = db.child("rides").child(ride_id)
    ride = ride_ref.get().val()

    if not ride:
        flash("Ride not found.", "warning")
        return redirect(url_for("rides.rides_list"))

    driver_id = ride.get("driver_id")
    if driver_id is None or driver_id != uid:
        flash("You can only cancel your own ride.", "danger")
        return redirect(url_for("rides.rides_list"))

    db.child("rides").child(ride_id).remove()
    db.child("ride_passengers").child(ride_id).remove()

    flash("Ride removed.", "info")
    return redirect(url_for("rides.rides_list"))