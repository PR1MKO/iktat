from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from app import db
from app.investigations.forms import INV_CATEGORY_CHOICES
from app.investigations.models import (
    InvestigationAttachment,
    InvestigationChangeLog,
    InvestigationNote,
)
from tests.helpers import (
    create_investigation,
    create_investigation_with_default_leiro,
    create_user,
    login,
    login_follow,
)


@pytest.fixture
def sample_investigation_with_data(app):
    with app.app_context():
        investigation = create_investigation(
            assignment_type="SZAKÉRTŐI",
            investigation_type="labor",
            external_case_number="EXT-42",
            other_identifier="OID-99",
            subject_name="Vizsgált Alany",
            institution_name="Beküldő Intézmény",
            maiden_name="Leánykori",
        )

        leiro_user = create_user(
            "leiro_reader",
            "secret",
            "leíró",
            screen_name="Leíró Olvasó",
        )
        expert_user = create_user(
            "expert_reader",
            "secret",
            "szakértő",
            screen_name="Szakértő",
        )

        investigation.describer_id = leiro_user.id
        investigation.expert1_id = expert_user.id
        db.session.commit()

        note = InvestigationNote(
            investigation_id=investigation.id,
            author_id=leiro_user.id,
            text="Jegyzet tartalma",
        )
        attachment = InvestigationAttachment(
            investigation_id=investigation.id,
            filename="jelentes.pdf",
            category="jelentes",
            uploaded_by=leiro_user.id,
        )
        change = InvestigationChangeLog(
            investigation_id=investigation.id,
            field_name="status",
            old_value="régi",
            new_value="új",
            edited_by=leiro_user.id,
        )
        db.session.add_all([note, attachment, change])
        db.session.commit()

        return investigation, leiro_user


@pytest.fixture
def investigation_with_default_leiro(app):
    with app.app_context():
        inv, leiro_user, _ = create_investigation_with_default_leiro()
        return inv, leiro_user


def test_leiro_elvegzem_assigned_sees_upload_and_notes(
    client, sample_investigation_with_data
):
    investigation, leiro_user = sample_investigation_with_data
    login_follow(client, leiro_user.username, "secret")

    response = client.get(f"/investigations/{investigation.id}/leiro/elvegzem")
    assert response.status_code == 200

    soup = BeautifulSoup(response.data, "html.parser")

    upload_form = soup.select_one("form#file-upload-form")
    assert upload_form is not None, "Upload form should be visible for assigned leíró"

    category_select = upload_form.select_one("select.category-select")
    assert category_select is not None
    option_values = {
        option.get("value")
        for option in category_select.find_all("option")
        if option.get("value")
    }
    expected_values = {choice[0] for choice in INV_CATEGORY_CHOICES if choice[0]}
    assert expected_values.issubset(option_values)

    notes_textarea = soup.select_one("textarea[name='text']")
    assert notes_textarea is not None
    add_btn = soup.select_one("button#add-note-btn")
    assert add_btn is not None
    assert f"/investigations/{investigation.id}/notes" in add_btn.get(
        "data-notes-url", ""
    )

    notes_list = soup.select_one("#notes-list")
    assert notes_list is not None


def test_leiro_default_fallback_sees_upload_and_notes(
    client, investigation_with_default_leiro
):
    investigation, leiro_user = investigation_with_default_leiro
    login_follow(client, leiro_user.username, "secret")

    response = client.get(f"/investigations/{investigation.id}/leiro/elvegzem")
    assert response.status_code == 200

    soup = BeautifulSoup(response.data, "html.parser")
    assert soup.select_one("form#file-upload-form") is not None
    assert soup.select_one("button#add-note-btn") is not None


@pytest.mark.parametrize("role_alias", ["leir", "LEIRO", "lei"])
def test_leiro_elvegzem_allows_legacy_role_alias(
    app, client, sample_investigation_with_data, role_alias
):
    investigation, _ = sample_investigation_with_data

    with app.app_context():
        alias_user = create_user(
            f"{role_alias.lower()}_reader",
            "secret",
            role_alias,
            screen_name=f"Alias {role_alias}",
        )
        investigation.describer_id = alias_user.id
        db.session.commit()

    login(client, alias_user.username, "secret")
    response = client.get(f"/investigations/{investigation.id}/leiro/elvegzem")
    assert response.status_code == 200


def test_leiro_elvegzem_unassigned_hides_controls(
    app, client, sample_investigation_with_data
):
    investigation, _ = sample_investigation_with_data
    with app.app_context():
        other_user = create_user(
            "leiro_unassigned",
            "secret",
            "leíró",
            screen_name="Másik Leíró",
        )

    login_follow(client, other_user.username, "secret")
    response = client.get(f"/investigations/{investigation.id}/leiro/elvegzem")
    assert response.status_code == 200

    soup = BeautifulSoup(response.data, "html.parser")
    assert soup.select_one("form#file-upload-form") is None
    assert soup.select_one("button#add-note-btn") is None
    assert soup.find(string="Feltöltés letiltva")
