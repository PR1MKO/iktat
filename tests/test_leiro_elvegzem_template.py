from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from app import db
from app.investigations.models import (
    InvestigationAttachment,
    InvestigationChangeLog,
    InvestigationNote,
)
from tests.helpers import create_investigation, create_user, login, login_follow


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


def test_leiro_elvegzem_renders_readonly_blocks(client, sample_investigation_with_data):
    investigation, leiro_user = sample_investigation_with_data
    login_follow(client, leiro_user.username, "secret")

    response = client.get(f"/investigations/{investigation.id}/leiro/elvegzem")
    assert response.status_code == 200

    soup = BeautifulSoup(response.data, "html.parser")

    for label in [
        "Ügyszám",
        "Végrehajtás módja",
        "Szakértő",
        "Leíró",
        "Vizsgálat típusa",
        "Születési idő",
    ]:
        assert soup.find(string=label), f"Missing label: {label}"

    assert soup.find(string="Dokumentumok")
    assert soup.find(string="Feltöltés letiltva")
    assert not soup.select("form[action*='upload']"), "Upload form must be hidden"

    assert soup.find(string="Megjegyzések")
    assert not soup.select("form[action*='note']"), "Add-note form must be hidden"

    assert soup.find(string="Változások")


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
