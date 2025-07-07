import time
import schedule
import pytz
from datetime import datetime
from app import create_app
from app.tasks import send_deadline_warning_emails

app = create_app()

BUDAPEST_TZ = pytz.timezone('Europe/Budapest')

# Only send email on weekdays at 8:00 AM Budapest time
def run_if_morning():
    now = datetime.now(BUDAPEST_TZ)
    if now.weekday() < 5 and now.hour == 8:
        with app.app_context():
            send_deadline_warning_email()

# Check every minute if it's time to run
schedule.every(1).minutes.do(run_if_morning)

print("[Scheduler] Deadline notifier is running...")
while True:
    schedule.run_pending()
    time.sleep(30)
