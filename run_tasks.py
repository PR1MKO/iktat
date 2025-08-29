import schedule
import time
from app import create_app
from app.tasks import send_deadline_warning_email
from app.utils.time_utils import now_local



def main():
    app = create_app()
    with app.app_context():
        def job():
            now = now_local().strftime("%Y-%m-%d %H:%M")
            print(f"[{now}] Running deadline warning task...")
            count = send_deadline_warning_email()
            print(f"Email sent for {count} upcoming case(s).")

        # Schedule: 8:00 AM CET, Mon-Fri
        schedule.every().monday.at("08:00").do(job)
        schedule.every().tuesday.at("08:00").do(job)
        schedule.every().wednesday.at("08:00").do(job)
        schedule.every().thursday.at("08:00").do(job)
        schedule.every().friday.at("08:00").do(job)

        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == "__main__":
    main()