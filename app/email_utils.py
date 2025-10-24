from flask_mail import Message
from flask import current_app
from . import mail

def send_email(subject, recipients, body):
    """
    Best-effort email sender.
    Returns True on success, False on any failure.
    Never raises (so requests won't 500 due to email).
    """
    try:
        if not recipients:
            return False

        # Allow disabling outbound mail (e.g., on Render while testing)
        if current_app.config.get("MAIL_SUPPRESS_SEND"):
            print("MAIL_SUPPRESS_SEND=True — skipping email:", subject, recipients)
            return True

        msg = Message(subject=subject, recipients=recipients, body=body)
        mail.send(msg)
        return True
    except Exception as e:
        # Log but do not crash the request
        print("EMAIL ERROR:", repr(e))
        return False


def send_booking_emails(appointment):
    """
    Sends confirmation emails to patient and doctor (best-effort).
    Returns True only if both sends succeed; otherwise False.
    """
    ok1 = send_email(
        subject="Appointment Confirmed",
        recipients=[appointment.patient.email],
        body=(
            f"Hi {appointment.patient.full_name},\n\n"
            f"Your appointment with Dr. {appointment.doctor.full_name} is confirmed on "
            f"{appointment.date.strftime('%d-%m-%Y')} at {appointment.time.strftime('%H:%M')}.\n\n— Clinic"
        ),
    )
    ok2 = send_email(
        subject="New Appointment Booked",
        recipients=[appointment.doctor.email],
        body=(
            f"Hello Dr. {appointment.doctor.full_name},\n\n"
            f"New appointment booked with {appointment.patient.full_name} on "
            f"{appointment.date.strftime('%d-%m-%Y')} at {appointment.time.strftime('%H:%M')}.\n\n— Clinic"
        ),
    )
    return ok1 and ok2
