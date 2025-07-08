from app.models import User, db

def test_create_user(app):
    with app.app_context():
        user = User(username="testuser", role="admin")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

        loaded = User.query.filter_by(username="testuser").first()
        assert loaded is not None
        assert loaded.check_password("testpass")