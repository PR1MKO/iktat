"""Simple script to test SMTP connectivity.

Credentials are loaded from environment variables to avoid
hard-coding sensitive information in source control.
Set SMTP_USER and SMTP_PASS before running.
"""

import os
import smtplib

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


def main() -> None:
    """Attempt to log in to the configured SMTP server."""

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        raise ValueError(
            "SMTP_USER and SMTP_PASSWORD environment variables must be set"
        )

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        print("Connected and logged in!")
        server.quit()
    except Exception as e:  # pragma: no cover - manual testing helper
        print("Error:", e)


if __name__ == "__main__":
    main()
