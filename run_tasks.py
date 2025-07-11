import schedule
import time
import pytz
from datetime import datetime
from app import create_app
from app.tasks import send_deadline_warning_email

# Timezone for Budapest
budapest = pytz.timezone("Europe/Budapest")

app = create_app()
app.app_context().push()

def job():
    now = datetime.now(budapest).strftime("%Y-%m-%d %H:%M")
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
