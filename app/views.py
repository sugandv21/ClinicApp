import os
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_required, current_user
from . import db
from .models import User, DoctorAvailability, Appointment
from .email_utils import send_booking_emails, send_email

main_bp = Blueprint('main', __name__, url_prefix='')


@main_bp.route('/')
def index():
    doctors = User.query.filter_by(is_doctor=True).all()
    return render_template('index.html', doctors=doctors)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_doctor:
        appts = Appointment.query.filter_by(doctor_id=current_user.id).order_by(
            Appointment.date, Appointment.time
        ).all()
        return render_template('doctor_dashboard.html', appts=appts)
    else:
        my = Appointment.query.filter_by(patient_id=current_user.id).order_by(
            Appointment.date, Appointment.time
        ).all()
        return render_template('patient_dashboard.html', appts=my)


# ---------- Doctor: manage availability ----------
@main_bp.route('/doctor/schedule', methods=['GET', 'POST'])
@login_required
def doctor_schedule():
    if not current_user.is_doctor:
        abort(403)
    if request.method == 'POST':
        try:
            d = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            start = datetime.strptime(request.form['start_time'], '%H:%M').time()
            end = datetime.strptime(request.form['end_time'], '%H:%M').time()
            slot = int(request.form['slot_minutes'])
            if start >= end:
                flash('End time must be after start time.', 'warning')
                return redirect(url_for('main.doctor_schedule'))
            av = DoctorAvailability(
                doctor_id=current_user.id, date=d, start_time=start, end_time=end, slot_minutes=slot
            )
            db.session.add(av)
            db.session.commit()
            flash('Availability saved.', 'success')
            return redirect(url_for('main.doctor_schedule'))
        except Exception as e:
            db.session.rollback()
            print("SCHEDULE ERROR:", repr(e))
            flash('Failed to save availability. Please check the inputs.', 'danger')
            return redirect(url_for('main.doctor_schedule'))

    avail = DoctorAvailability.query.filter_by(doctor_id=current_user.id).order_by(
        DoctorAvailability.date.desc()
    ).all()
    return render_template('doctor_schedule.html', avail=avail)


def generate_slots(av: DoctorAvailability):
    slots = []
    cur_dt = datetime.combine(av.date, av.start_time)
    end_dt = datetime.combine(av.date, av.end_time)
    delta = timedelta(minutes=av.slot_minutes)
    # slot is [cur_dt, cur_dt+delta); last slot starts at or before end-delta
    while cur_dt + delta <= end_dt:
        slots.append(cur_dt.time())
        cur_dt += delta
    return slots


@main_bp.route('/doctors')
def doctors_list():
    doctors = User.query.filter_by(is_doctor=True).all()
    return render_template('index.html', doctors=doctors)


# ---------- Patient: book appointment ----------
@main_bp.route('/doctors/<int:doctor_id>/book', methods=['GET', 'POST'])
@login_required
def book_slot(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    if not doctor.is_doctor:
        abort(404)

    selected_date_str = request.values.get('date')
    selected_date = (
        datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        if selected_date_str else date.today()
    )

    # Build list of available times for this doctor + date
    avails = DoctorAvailability.query.filter_by(doctor_id=doctor.id, date=selected_date).all()
    available_times = []
    for av in avails:
        slots = generate_slots(av)
        booked = {
            a.time for a in Appointment.query.filter_by(
                doctor_id=doctor.id, date=selected_date
            ).all()
        }
        for t in slots:
            if t not in booked:
                available_times.append(t)
    available_times = sorted(set(available_times))

    if request.method == 'POST':
        try:
            chosen = request.form.get('time')
            if not chosen:
                flash('Please choose a time.', 'warning')
                return redirect(url_for('main.book_slot', doctor_id=doctor.id, date=selected_date.isoformat()))

            chosen_time = datetime.strptime(chosen, '%H:%M').time()

            # Double-check availability just before saving
            exists = Appointment.query.filter_by(
                doctor_id=doctor.id, date=selected_date, time=chosen_time
            ).first()
            if exists:
                flash('Sorry, that slot just got booked. Pick another.', 'danger')
                return redirect(url_for('main.book_slot', doctor_id=doctor.id, date=selected_date.isoformat()))

            appt = Appointment(
                doctor_id=doctor.id,
                patient_id=current_user.id,
                date=selected_date,
                time=chosen_time,
                status='confirmed'
            )
            db.session.add(appt)
            db.session.commit()

            sent = send_booking_emails(appt)  # best-effort; never raises
            if sent:
                flash('Appointment booked and emails sent.', 'success')
            else:
                flash('Appointment booked. Email delivery failed (check email settings).', 'warning')

            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            print("BOOKING ERROR:", repr(e))
            flash('Booking failed due to a server error. Please try again.', 'danger')
            return redirect(url_for('main.book_slot', doctor_id=doctor.id, date=selected_date.isoformat()))

    return render_template('book_slot.html', doctor=doctor, selected_date=selected_date, available_times=available_times)


# ---------- Doctor: update appointment status ----------
@main_bp.route('/appointments/<int:appt_id>/status', methods=['POST'])
@login_required
def update_status(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if not current_user.is_doctor or appt.doctor_id != current_user.id:
        abort(403)
    new_status = request.form.get('status', 'confirmed')
    try:
        appt.status = new_status
        db.session.commit()
        flash('Appointment status updated.', 'success')
    except Exception as e:
        db.session.rollback()
        print("STATUS UPDATE ERROR:", repr(e))
        flash('Failed to update status.', 'danger')
    return redirect(url_for('main.dashboard'))


# ---------- Patient: my appointments ----------
@main_bp.route('/my-appointments')
@login_required
def my_appointments():
    my = Appointment.query.filter_by(patient_id=current_user.id).order_by(
        Appointment.date, Appointment.time
    ).all()
    return render_template('appointments.html', appts=my)


# ---------- Cron: send reminders (Render Cron hits this endpoint) ----------
@main_bp.route('/tasks/send_reminders')
def send_reminders():
    token = request.args.get('token')
    expected = os.getenv('CRON_SECRET', '')
    if expected and token != expected:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401

    now = datetime.utcnow()
    soon = now + timedelta(hours=24)  # send reminders for next 24h
    q = Appointment.query.filter(
        Appointment.status == 'confirmed',
        Appointment.reminder_sent == False,  # noqa: E712
    ).all()

    sent = 0
    for appt in q:
        appt_dt_utc = datetime.combine(appt.date, appt.time)
        if now <= appt_dt_utc <= soon:
            # notify both, best-effort
            p_ok = send_email(
                subject="Appointment Reminder",
                recipients=[appt.patient.email],
                body=(
                    f"Reminder: Appointment with Dr. {appt.doctor.full_name} on "
                    f"{appt.date.strftime('%d-%m-%Y')} at {appt.time.strftime('%H:%M')}."
                )
            )
            d_ok = send_email(
                subject="Upcoming Appointment Reminder",
                recipients=[appt.doctor.email],
                body=(
                    f"Reminder: Appointment with {appt.patient.full_name} on "
                    f"{appt.date.strftime('%d-%m-%Y')} at {appt.time.strftime('%H:%M')}."
                )
            )
            if p_ok or d_ok:
                appt.reminder_sent = True
                sent += 1
    db.session.commit()
    return jsonify({'ok': True, 'sent': sent})
