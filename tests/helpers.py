# tests/helpers.py
from datetime import date

from app.investigations.models import Investigation
from app.investigations.utils import generate_case_number
from app.models import User, db


def create_user(username="admin", password="secret", role="admin", **kw):
    # Idempotent user creation: update existing instead of violating UNIQUE
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
            if getattr(existing, k, None) != v:
                setattr(existing, k, v)
                changed = True
        if changed:
            db.session.commit()
        return existing

    user = User(
        username=username,
        screen_name=kw.get("screen_name", username),
        role=role,
        **{k: v for k, v in kw.items() if k not in {"screen_name"}},
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
        "status": "beérkezett",
    }
    data.update(kwargs)
    if data.get("assignment_type") == "SZAKÉRTŐI" and data.get("assigned_expert_id"):
        data.setdefault("expert1_id", data["assigned_expert_id"])
        data.setdefault("status", "szignálva")
    inv = Investigation(**data)
    db.session.add(inv)
    db.session.commit()
    return inv


def create_investigation_with_default_leiro(role: str = "leíró"):
    leiro = create_user(f"default_{role}_leiro", "secret", role)
    expert = create_user(
        f"default_{role}_expert",
        "secret",
        "szakértő",
        default_leiro_id=leiro.id,
    )
    inv = create_investigation()
    inv.expert1_id = expert.id
    inv.describer_id = None
    db.session.commit()
    return inv, leiro, expert
