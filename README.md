# Clinic Appointment Booking (Flask)

## Run locally
python -m venv venv
venv\Scripts\activate  # Windows
# or source venv/bin/activate (Mac/Linux)

pip install -r requirements.txt
# Create .env with your secrets (see .env in repo)
python wsgi.py  # http://127.0.0.1:5000

## Deploy on Render
- Push this repo to GitHub.
- Create a new **Web Service**:
  - Build: `pip install -r requirements.txt`
  - Start: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
  - Add env vars from `.env` (use Gmail App Password).
- Add **Cron Job** from `render.yaml` or via dashboard to hit `/tasks/send_reminders?token=CRON_SECRET`.

## Roles & Flow
- Register **Doctor** and **Patient**.
- Doctor sets **Availability** (date/time/slot).
- Patient books; emails go to both sides.
