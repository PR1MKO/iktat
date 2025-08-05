import time
import schedule
from app import create_app
from app.tasks import send_deadline_warning_email
from app.utils.time_utils import now_local

app = create_app()

# Only send email on weekdays at 8:00 AM Budapest time
def run_if_morning():
    now = now_local()
    if now.weekday() < 5 and now.hour == 8:
        with app.app_context():
            send_deadline_warning_email()

# Check every minute if it's time to run
schedule.every(1).minutes.do(run_if_morning)

print("[Scheduler] Deadline notifier is running...")
while True:
    schedule.run_pending()
    time.sleep(30)
