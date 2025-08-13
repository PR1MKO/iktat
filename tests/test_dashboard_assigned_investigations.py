from tests.helpers import create_user, create_investigation, login


def test_assigned_investigation_visible_on_dashboard(client, app):
    with app.app_context():
        user = create_user('szak1', 'pw', role='szakértő')
        inv = create_investigation(
            case_number='V:0009/2025',
            assignment_type='SZAKÉRTŐI',
            assigned_expert_id=user.id,
        )
        inv_id = inv.id

    with client:
        login(client, 'szak1', 'pw')
        resp = client.get('/dashboard')
        assert b'V:0009/2025' in resp.data
        assert b'has been signalled to you' in resp.data
        assert f'/investigations/{inv_id}/view'.encode() in resp.data