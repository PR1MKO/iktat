from app import create_app, db
from app.models import User, Case

app = create_app()

with app.app_context():
    cases = Case.query.all()
    for case in cases:
        if case.expert_1:
            user = User.query.filter_by(username=case.expert_1).first()
            if user and user.screen_name:
                case.expert_1 = user.screen_name
        if case.expert_2:
            user = User.query.filter_by(username=case.expert_2).first()
            if user and user.screen_name:
                case.expert_2 = user.screen_name
        if case.describer:
            user = User.query.filter_by(username=case.describer).first()
            if user and user.screen_name:
                case.describer = user.screen_name
        if case.tox_expert:
            user = User.query.filter_by(username=case.tox_expert).first()
            if user and user.screen_name:
                case.tox_expert = user.screen_name
    db.session.commit()
    print(f"Updated {len(cases)} cases.")