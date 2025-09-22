import pytest
from flask import url_for

from app.models import Case, db
from tests.helpers import create_investigation, create_user, login


@pytest.fixture
def szak_setup(app):
    with app.app_context():
        user = create_user(
            "szak_user",
            "secret",
            "szakértő",
            screen_name="Dr. Szak",
        )
        other = create_user(
            "masik_szak",
            "secret",
            "szakértő",
            screen_name="Másik Szak",
        )

        case_assigned = Case(
            case_number="B-001",
            deceased_name="Rámbízott",
            status="beérkezett",
        )
        case_assigned.expert_1 = user.screen_name

        case_other = Case(
            case_number="B-002",
            deceased_name="Más",
            status="beérkezett",
        )
        case_other.expert_1 = other.screen_name

        db.session.add_all([case_assigned, case_other])
        db.session.commit()

        inv_assigned = create_investigation(
            case_number="V-001",
            expert1_id=user.id,
            status="beérkezett",
        )
        inv_other = create_investigation(
            case_number="V-002",
            expert1_id=other.id,
            status="beérkezett",
        )

        return {
            "user": {"username": user.username, "password": "secret", "id": user.id},
            "case_assigned": {
                "id": case_assigned.id,
                "number": case_assigned.case_number,
            },
            "case_other": {
                "id": case_other.id,
                "number": case_other.case_number,
            },
            "inv_assigned": {
                "id": inv_assigned.id,
                "number": inv_assigned.case_number,
            },
            "inv_other": {
                "id": inv_other.id,
                "number": inv_other.case_number,
            },
        }


def _get(client, path):
    response = client.get(path)
    assert response.status_code == 200
    return response


def test_ugyeim_lists_only_assigned_items(client, szak_setup):
    creds = szak_setup["user"]
    with client:
        login(client, creds["username"], creds["password"])
        resp = _get(client, "/ugyeim")

    html = resp.get_data(as_text=True)
    assert "Elvégzendő" in html
    assert "Boncolások" in html
    assert "Vizsgálatok" in html
    assert szak_setup["case_assigned"]["number"] in html
    assert szak_setup["case_other"]["number"] not in html
    assert szak_setup["inv_assigned"]["number"] in html
    assert szak_setup["inv_other"]["number"] not in html


def test_ugyeim_layout_has_card_columns(client, szak_setup):
    creds = szak_setup["user"]
    with client:
        login(client, creds["username"], creds["password"])
        resp = _get(client, "/ugyeim")

    html = resp.get_data(as_text=True)
    assert html.count("card shadow-sm") >= 2
    assert html.count('class="col-12 col-lg-6"') >= 2
    assert '<h2 class="h5 mb-0">Boncolások</h2>' in html
    assert '<h2 class="h5 mb-0">Vizsgálatok</h2>' in html


def test_ugyeim_has_links_and_actions(client, app, szak_setup):
    creds = szak_setup["user"]
    with client:
        login(client, creds["username"], creds["password"])
        resp = _get(client, "/ugyeim")

    html = resp.get_data(as_text=True)
    with app.test_request_context():
        case_link = url_for(
            "auth.case_detail", case_id=szak_setup["case_assigned"]["id"]
        )
        inv_link = url_for(
            "investigations.detail_investigation",
            id=szak_setup["inv_assigned"]["id"],
        )
        case_action = url_for(
            "main.elvegzem", case_id=szak_setup["case_assigned"]["id"]
        )
        inv_action = url_for(
            "main.elvegzem",
            case_id=szak_setup["inv_assigned"]["id"],
            type="investigation",
        )

    assert f'href="{case_link}"' in html
    assert f'href="{inv_link}"' in html
    assert "Megtekintés" not in html
    assert f'href="{case_action}"' in html
    assert f'href="{inv_action}"' in html


def test_investigation_elvegzem_redirects_to_detail(client, app, szak_setup):
    creds = szak_setup["user"]
    inv_id = szak_setup["inv_assigned"]["id"]

    with client:
        login(client, creds["username"], creds["password"])
        resp = client.get(f"/ugyeim/{inv_id}/elvegzem?type=investigation")

    assert resp.status_code == 302
    with app.test_request_context():
        expected = url_for("investigations.detail_investigation", id=inv_id)
    assert resp.headers["Location"].endswith(expected)
