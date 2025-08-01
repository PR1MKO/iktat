from app.models import User, db


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
