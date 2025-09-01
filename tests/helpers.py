from datetime import date

from app.investigations.models import Investigation
from app.investigations.utils import generate_case_number
from app.models import User, db


def create_user(username="admin", password="secret", role="admin", **kw):
    with db.session.no_autoflush:
        existing = User.query.filter_by(username=username).first()
    if existing:
        changed = False
        if role and existing.role != role:
            existing.role = role
            changed = True
        if password:
            existing.set_password(password)
            changed = True
        for k, v in kw.items():
            setattr(existing, k, v)
            changed = True
        if changed:
            db.session.commit()
        return existing

    user = User(
        username=username, screen_name=kw.get("screen_name", username), role=role, **kw
    )
    if password:
        user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username, password):
    # Keep redirects OFF so tests expecting 302 (like test_login_success) pass.
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def login_follow(client, username, password):
    # Use this when you need an authenticated session within the same client context.
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def create_investigation(**kwargs):
    data = {
        "case_number": kwargs.get("case_number") or generate_case_number(db.session),
        "subject_name": "Subject",
        "mother_name": "Mother",
        "birth_place": "Place",
        "birth_date": date(2000, 1, 1),
        "taj_number": "123456789",
        "residence": "Address",
        "citizenship": "HU",
        "institution_name": "Inst",
    }
    data.update(kwargs)
    inv = Investigation(**data)
    db.session.add(inv)
    db.session.commit()
    return inv
