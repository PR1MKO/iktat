import time
import schedule
from app import create_app
from app.tasks import send_deadline_warning_email
from app.utils.time_utils import now_local

def main():
    app = create_app()
    with app.app_context():
        # Only send email on weekdays at 8:00 AM Budapest time
        def run_if_morning():
            now = now_local()
            if now.weekday() < 5 and now.hour == 8:
                send_deadline_warning_email()
                
        # Check every minute if it's time to run
        schedule.every(1).minutes.do(run_if_morning)

        print("[Scheduler] Deadline notifier is running...")
        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    main()
