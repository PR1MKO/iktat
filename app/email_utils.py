from flask_mail import Message
from flask import current_app

from . import mail


def send_email(subject, recipients, body):
    """Send an email using Flask-Mail.

    If ``MAIL_DEFAULT_SENDER`` is not configured the function falls back to
    ``MAIL_USERNAME`` to avoid ``AssertionError`` from Flask-Mail.
    """
    sender = (
        current_app.config.get("MAIL_DEFAULT_SENDER")
        or current_app.config.get("MAIL_USERNAME")
    )
    msg = Message(subject, recipients=recipients, body=body, sender=sender)
    mail.send(msg)
