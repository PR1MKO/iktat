from app import create_app
from config import TestingConfig

def test_app_starts():
    app = create_app(TestingConfig)
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Forensic Case Tracker" in response.data or b"Forensic" in response.data