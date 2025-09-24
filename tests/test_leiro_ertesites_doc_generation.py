from pathlib import Path
from zipfile import ZipFile

import pytest

from app import db
from app.paths import ensure_investigation_folder
from tests.helpers import (
    create_investigation,
    create_investigation_with_default_leiro,
    create_user,
    login_follow,
)

ERTESITES_FILENAME = "ertesites_szakertoi_vizsgalatrol.docx"


@pytest.mark.usefixtures("app")
def test_leiro_ertesites_form_generates_document(app, client, tmp_path):
    with app.app_context():
        inv, leiro_user, expert_user = create_investigation_with_default_leiro()
        inv.subject_name = "Vizsgált Alany"
        inv.external_case_number = "EXT-42"
        inv.institution_name = "Beküldő Intézmény"
        db.session.commit()

        leiro_user.full_name = "Leíró Példa"
        expert_user.full_name = "Szakértő Példa"
        db.session.commit()

        case_number = inv.case_number
        inv_id = inv.id
        login_username = leiro_user.username

        storage_root = tmp_path / "generated-investigations"
        app.config["INVESTIGATION_UPLOAD_FOLDER"] = str(storage_root)
        app.config["UPLOAD_INVESTIGATIONS_ROOT"] = str(storage_root)

        case_folder = ensure_investigation_folder(case_number)
        template_dir = case_folder / "DO-NOT-EDIT"
        template_dir.mkdir(parents=True, exist_ok=True)

        from docx import Document

        template_dst = template_dir / ERTESITES_FILENAME
        doc = Document()
        doc.add_paragraph("Címzett: {{cimzett}}")
        doc.add_paragraph("Külső ügyirat: {{kulso_ugyirat}}")
        doc.add_paragraph("Ügyszám: {{iktatasi_szam}}")
        doc.add_paragraph("Jegyzőkönyv vezető: {{jkv_vezeto}}")
        doc.add_paragraph("Beküldő: {{kirendelo}}")
        doc.add_paragraph("Szak: {{szak}}")
        doc.add_paragraph("Létrehozva: {{creation_date}}")
        doc.add_paragraph("Titulus: {{titulus}}")
        doc.add_paragraph("Vizsgálat időpontja: {{vizsg_date}}")
        doc.save(template_dst)

    login_follow(client, login_username, "secret")

    get_resp = client.get(f"/investigations/{inv_id}/leiro/ertesites_form")
    assert get_resp.status_code == 200

    post_resp = client.post(
        f"/investigations/{inv_id}/leiro/ertesites_form",
        data={"titulus": "Dr.", "vizsg_date": "2025-09-24T10:30"},
        follow_redirects=False,
    )
    assert post_resp.status_code in {302, 303}

    safe_case = case_number.replace(":", "-").replace("/", "-").strip(" .")
    output_path = (
        Path(app.config["INVESTIGATION_UPLOAD_FOLDER"]) / safe_case / ERTESITES_FILENAME
    )
    assert output_path.exists()

    with ZipFile(output_path) as bundle:
        document_xml = bundle.read("word/document.xml").decode("utf-8")

    assert "Vizsgált Alany" in document_xml
    assert "EXT-42" in document_xml
    assert "Beküldő Intézmény" in document_xml
    assert "Leíró Példa" in document_xml
    assert "Szakértő Példa" in document_xml
    assert "Dr." in document_xml
    assert "2025.09.24 10:30" in document_xml
    assert "{{" not in document_xml


@pytest.mark.usefixtures("app")
def test_leiro_ertesites_form_blocks_non_leiro(app, client):
    with app.app_context():
        inv = create_investigation()
        user = create_user("not_leiro", "secret", "admin")
        inv_id = inv.id

    login_follow(client, user.username, "secret")
    post_resp = client.post(
        f"/investigations/{inv_id}/leiro/ertesites_form",
        data={"titulus": "Dr.", "vizsg_date": "2025-09-24T10:30"},
        follow_redirects=False,
    )
    assert post_resp.status_code in {302, 403}
