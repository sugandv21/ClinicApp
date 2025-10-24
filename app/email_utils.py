from flask_mail import Message
from . import mail

def send_email(subject, recipients, body):
    if not recipients:
        return
    msg = Message(subject=subject, recipients=recipients, body=body)
    mail.send(msg)

def send_booking_emails(appointment):
    # Notify patient
    send_email(
        subject="Appointment Confirmed",
        recipients=[appointment.patient.email],
        body=f"Hi {appointment.patient.full_name},\n\n"
             f"Your appointment with Dr. {appointment.doctor.full_name} is confirmed on "
             f"{appointment.date.strftime('%d-%m-%Y')} at {appointment.time.strftime('%H:%M')}.\n\n"
             f"— Clinic"
    )
    # Notify doctor
    send_email(
        subject="New Appointment Booked",
        recipients=[appointment.doctor.email],
        body=f"Hello Dr. {appointment.doctor.full_name},\n\n"
             f"New appointment booked with {appointment.patient.full_name} on "
             f"{appointment.date.strftime('%d-%m-%Y')} at {appointment.time.strftime('%H:%M')}.\n\n"
             f"— Clinic"
    )
