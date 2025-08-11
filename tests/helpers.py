from datetime import date

from app.models import User, db
from app.investigations.models import Investigation
from app.investigations.utils import generate_case_number


def create_user(username="admin", password="secret", role="admin"):
    user = User(username=username, screen_name=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username, password):
    return client.post(
        '/login',
        data={'username': username, 'password': password},
        follow_redirects=False,
    )

def create_investigation(**kwargs):
    data = {
        'case_number': kwargs.get('case_number') or generate_case_number(db.session),
        'subject_name': 'Subject',
        'mother_name': 'Mother',
        'birth_place': 'Place',
        'birth_date': date(2000, 1, 1),
        'taj_number': '123456789',
        'residence': 'Address',
        'citizenship': 'HU',
        'institution_name': 'Inst',
    }
    data.update(kwargs)
    inv = Investigation(**data)
    db.session.add(inv)
    db.session.commit()
    return inv