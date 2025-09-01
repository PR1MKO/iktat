from app.models import Case, TaskMessage, db
from app.utils.time_utils import now_local
from tests.helpers import create_user, login


def test_case_removed_from_feladataim_after_start(client, app):
    with app.app_context():
        expert = create_user("doc", "pw", role="szakértő")
        case = Case(
            case_number="TASK1", expert_1=expert.screen_name, status="szignálva"
        )
        db.session.add(case)
        db.session.commit()
        msg = TaskMessage(
            user_id=expert.id,
            recipient=expert.username,
            case_id=case.id,
            message="Assigned",
            timestamp=now_local(),
        )
        db.session.add(msg)
        db.session.commit()
        cid = case.id

    with client:
        login(client, "doc", "pw")
        resp = client.get("/dashboard")
        assert b"TASK1" in resp.data

        client.get(f"/ugyeim/{cid}/elvegzem")
        resp = client.get("/dashboard")
        assert b"TASK1" not in resp.data

    with app.app_context():
        updated = db.session.get(Case, cid)
        assert updated.started_by_expert is True
