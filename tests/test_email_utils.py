from unittest.mock import patch

from app import create_app, mail
from app.email_utils import send_email
from config import TestingConfig


def test_send_email_handles_error(caplog):
    app = create_app(TestingConfig)
    with app.app_context():
        with patch.object(mail, "send", side_effect=Exception("fail")):
            send_email("subject", ["test@example.com"], "body")
        assert "Failed to send email" in caplog.text
